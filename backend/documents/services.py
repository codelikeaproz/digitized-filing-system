from django.db import transaction
from django.utils import timezone

from .models import Document, Folder


def _folder_tree_ids(folder):
    ids = [folder.id]
    for child in folder.children.all():
        ids.extend(_folder_tree_ids(child))
    return ids


@transaction.atomic
def soft_delete_folder(folder, user):
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
    folder_ids = _folder_tree_ids(folder)
    documents = list(Document.objects.filter(folder_id__in=folder_ids))
    document_count = len(documents)

    for document in documents:
        if document.file:
            document.file.delete(save=False)

    Folder.objects.filter(id__in=folder_ids).delete()
    return document_count
