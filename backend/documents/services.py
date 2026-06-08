"""
Folder and document lifecycle services.

Purpose:
    Shared transactional logic for soft delete, restore, and permanent delete
    of folder trees (including nested subfolders and documents).

Used by:
    documents/views.py — RecycleBinRestoreAPIView, RecycleBinDeleteAPIView,
                         FolderViewSet.destroy
"""
from django.db import transaction
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from notifications.storage_alerts import check_storage_thresholds
from orgunits.storage import bytes_to_mb, recalculate_org_unit_storage, subtract_storage_usage

from .models import Document, Folder


def build_folder_path_map(folder_ids):
    """
    Build folder_id -> full path (Parent > Child) without N+1 parent lookups.
    Walks ancestors until the root for each requested folder id.
    """
    normalized_ids = {folder_id for folder_id in folder_ids if folder_id}
    if not normalized_ids:
        return {}

    folders_by_id = {}
    pending = set(normalized_ids)
    while pending:
        rows = Folder.objects.filter(id__in=pending).values("id", "name", "parent_id")
        pending = set()
        for row in rows:
            folders_by_id[row["id"]] = row
            parent_id = row["parent_id"]
            if parent_id and parent_id not in folders_by_id:
                pending.add(parent_id)

    def path_for(folder_id):
        parts = []
        current = folder_id
        visited = set()
        while current and current in folders_by_id:
            if current in visited:
                break
            visited.add(current)
            folder = folders_by_id[current]
            parts.append(folder["name"])
            current = folder["parent_id"]
        return " > ".join(reversed(parts))

    return {folder_id: path_for(folder_id) for folder_id in normalized_ids if folder_id in folders_by_id}


def resolve_document_file_path(document, path_map=None):
    """Return the live folder path for a document; folder FK is authoritative."""
    if document.folder_id:
        if path_map is not None:
            return path_map.get(document.folder_id, "")
        return document.folder.get_full_path()
    return document.file_path or ""


def resolve_document_location_path(document, path_map):
    return resolve_document_file_path(document, path_map=path_map)


def refresh_document_file_paths_for_folder_tree(root_folder):
    """Recompute and persist file_path for all documents in a folder subtree."""
    folder_ids = _folder_tree_ids(root_folder)
    path_map = build_folder_path_map(folder_ids)
    documents = list(Document.objects.filter(folder_id__in=folder_ids))
    to_update = []
    for document in documents:
        new_path = path_map.get(document.folder_id, "")
        if document.file_path != new_path:
            document.file_path = new_path
            to_update.append(document)
    if to_update:
        Document.objects.bulk_update(to_update, ["file_path"])
    return len(to_update)


def resolve_folder_location_path(folder, path_map):
    return path_map.get(folder.id, "")


def _folder_tree_ids(folder):
    ids = [folder.id]
    for child in folder.children.all():
        ids.extend(_folder_tree_ids(child))
    return ids


@transaction.atomic
def soft_delete_folder(folder, user):
    """
    Mark folder subtree and contained documents as deleted (Recycle Bin).
    Returns the number of documents soft-deleted.
    """
    now = timezone.now()
    folder_ids = _folder_tree_ids(folder)

    Folder.objects.filter(id__in=folder_ids).update(
        is_deleted=True,
        deleted_at=now,
        deleted_by=user,
    )
    document_count = Document.objects.filter(
        folder_id__in=folder_ids,
        is_deleted=False,
    ).update(
        is_deleted=True,
        deleted_at=now,
        deleted_by=user,
    )
    return document_count


@transaction.atomic
def restore_folder(folder, user=None):
    """Restore folder subtree and documents whose parent folder is active."""
    folder_ids = _folder_tree_ids(folder)

    Folder.objects.filter(id__in=folder_ids).update(
        is_deleted=False,
        deleted_at=None,
        deleted_by=None,
    )
    document_count = Document.objects.filter(
        folder_id__in=folder_ids,
        is_deleted=True,
        folder__is_deleted=False,
    ).update(
        is_deleted=False,
        deleted_at=None,
        deleted_by=None,
    )
    return document_count


@transaction.atomic
def permanently_delete_folder(folder, user=None):
    """Hard-delete folder subtree, documents, and media files (irreversible)."""
    folder_ids = _folder_tree_ids(folder)
    documents = list(Document.objects.filter(folder_id__in=folder_ids).select_related("folder__org_unit"))
    document_count = len(documents)
    org_unit = folder.org_unit
    total_bytes = sum(document.file_size or 0 for document in documents)

    for document in documents:
        if document.file:
            document.file.delete(save=False)

    Document.objects.filter(id__in=[document.id for document in documents]).delete()
    Folder.objects.filter(id__in=folder_ids).delete()

    if org_unit:
        if total_bytes:
            subtract_storage_usage(org_unit, total_bytes)
        else:
            recalculate_org_unit_storage(org_unit)

    check_storage_thresholds(user)
    return document_count


def _folder_is_descendant_of(folder, ancestor):
    current = folder
    while current.parent_id:
        if current.parent_id == ancestor.id:
            return True
        current = current.parent
    return False


def _parse_bulk_items(items):
    if not items:
        raise ValidationError({"message": "At least one item must be selected."})

    folder_ids = []
    document_ids = []
    for row in items:
        item_type = (row.get("type") or "").lower()
        item_id = row.get("id")
        if item_id in (None, ""):
            raise ValidationError({"message": "Each item must include an id."})
        try:
            normalized_id = int(item_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"message": "Invalid item id."}) from exc
        if item_type == "folder":
            folder_ids.append(normalized_id)
        elif item_type == "document":
            document_ids.append(normalized_id)
        else:
            raise ValidationError({"message": "Invalid item type."})
    return folder_ids, document_ids


def bulk_normalize_selection(items):
    """
    Deduplicate bulk recycle-bin selections.

    Returns root deleted folders and standalone deleted documents, excluding
    documents and child folders covered by a selected ancestor folder.
    """
    folder_ids, document_ids = _parse_bulk_items(items)

    selected_folders = list(
        Folder.objects.filter(id__in=folder_ids, is_deleted=True).select_related("org_unit", "parent")
    )
    if len(selected_folders) != len(set(folder_ids)):
        raise ValidationError({"message": "One or more selected folders were not found in the recycle bin."})

    root_folders = []
    for folder in selected_folders:
        if any(
            other.id != folder.id and _folder_is_descendant_of(folder, other)
            for other in selected_folders
        ):
            continue
        root_folders.append(folder)

    covered_folder_ids = set()
    for folder in root_folders:
        covered_folder_ids.update(_folder_tree_ids(folder))

    selected_documents = list(
        Document.objects.filter(id__in=document_ids, is_deleted=True).select_related("folder__org_unit")
    )
    if len(selected_documents) != len(set(document_ids)):
        raise ValidationError({"message": "One or more selected documents were not found in the recycle bin."})

    standalone_documents = [
        document
        for document in selected_documents
        if document.folder_id not in covered_folder_ids
    ]
    return root_folders, standalone_documents


def compute_bulk_delete_bytes(root_folders, standalone_documents):
    total_bytes = sum(document.file_size or 0 for document in standalone_documents)
    for folder in root_folders:
        folder_ids = _folder_tree_ids(folder)
        documents = Document.objects.filter(folder_id__in=folder_ids)
        total_bytes += sum(document.file_size or 0 for document in documents)
    return int(total_bytes)


def build_bulk_summary_metrics(root_folders, standalone_documents):
    total_bytes = compute_bulk_delete_bytes(root_folders, standalone_documents)
    return {
        "total_bytes": total_bytes,
        "total_storage_mb": round(float(bytes_to_mb(total_bytes)), 2),
    }


def validate_bulk_restore_selection(root_folders, standalone_documents):
    """Reject standalone documents whose parent folder is still deleted."""
    for document in standalone_documents:
        if document.folder.is_deleted:
            folder_name = document.folder.name if document.folder else "Unknown"
            raise ValidationError(
                {
                    "message": (
                        f"Cannot restore document '{document.title}'. Parent folder "
                        f"'{folder_name}' is still deleted. Restore the parent folder "
                        f"first or include it in your selection."
                    )
                }
            )


def _restore_document(document):
    if document.folder.is_deleted:
        folder_name = document.folder.name if document.folder else "Unknown"
        raise ValidationError(
            {
                "message": (
                    f"Cannot restore document '{document.title}'. Parent folder "
                    f"'{folder_name}' is still deleted. Restore the parent folder "
                    f"first or include it in your selection."
                )
            }
        )
    document.is_deleted = False
    document.deleted_at = None
    document.deleted_by = None
    document.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])


def _permanently_delete_document(document, user=None):
    org_unit = document.folder.org_unit if document.folder else None
    file_size = document.file_size or 0
    if document.file:
        document.file.delete(save=False)
    document.delete()
    if org_unit and file_size:
        subtract_storage_usage(org_unit, file_size)
    return file_size


@transaction.atomic
def bulk_restore_items(user, root_folders, standalone_documents):
    validate_bulk_restore_selection(root_folders, standalone_documents)
    documents_restored = 0
    folders_restored = len(root_folders)

    for folder in root_folders:
        documents_restored += restore_folder(folder, user)

    for document in standalone_documents:
        _restore_document(document)
        documents_restored += 1

    return {
        "folders_restored": folders_restored,
        "documents_restored": documents_restored,
        "total_restored": folders_restored + len(standalone_documents),
    }


@transaction.atomic
def bulk_permanent_delete_items(user, root_folders, standalone_documents):
    documents_deleted = 0
    folders_deleted = len(root_folders)
    bytes_released = 0

    for folder in root_folders:
        folder_ids = _folder_tree_ids(folder)
        documents = list(Document.objects.filter(folder_id__in=folder_ids))
        bytes_released += sum(document.file_size or 0 for document in documents)
        documents_deleted += permanently_delete_folder(folder, user)

    for document in standalone_documents:
        bytes_released += _permanently_delete_document(document, user)
        documents_deleted += 1

    if user:
        check_storage_thresholds(user)

    return {
        "folders_deleted": folders_deleted,
        "documents_deleted": documents_deleted,
        "total_deleted": folders_deleted + len(standalone_documents),
        "bytes_released": int(bytes_released),
        "storage_released_mb": round(float(bytes_to_mb(bytes_released)), 2),
    }
