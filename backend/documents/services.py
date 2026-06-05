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

from orgunits.storage import recalculate_org_unit_storage, subtract_storage_usage

from .models import Document, Folder


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

    return document_count
