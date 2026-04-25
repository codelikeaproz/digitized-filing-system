from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone

from documents.models import Document, Folder


LOCAL_APP_LABELS = {"accounts", "auditlogs", "documents", "orgunits"}


class Command(BaseCommand):
    help = "Normalize local DFS timestamps to timezone-aware values and repair deleted item timestamps."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report affected rows without saving changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        updated = 0

        for model in apps.get_models():
            if model._meta.app_label not in LOCAL_APP_LABELS:
                continue

            datetime_fields = [
                field
                for field in model._meta.fields
                if isinstance(field, models.DateTimeField)
            ]
            if not datetime_fields:
                continue

            for obj in model.objects.all().iterator():
                update_fields = []
                for field in datetime_fields:
                    value = getattr(obj, field.name)
                    if value and timezone.is_naive(value):
                        setattr(
                            obj,
                            field.name,
                            timezone.make_aware(value, timezone.get_current_timezone()),
                        )
                        update_fields.append(field.name)

                if update_fields:
                    updated += 1
                    if not dry_run:
                        obj.save(update_fields=update_fields)

        now = timezone.now()
        missing_folder_timestamps = Folder.objects.filter(is_deleted=True, deleted_at__isnull=True)
        missing_document_timestamps = Document.objects.filter(is_deleted=True, deleted_at__isnull=True)
        active_documents_under_deleted_folders = Document.objects.filter(is_deleted=False, folder__is_deleted=True)

        folder_count = missing_folder_timestamps.count()
        document_count = missing_document_timestamps.count()
        orphan_count = active_documents_under_deleted_folders.count()

        if not dry_run:
            missing_folder_timestamps.update(deleted_at=now)
            missing_document_timestamps.update(deleted_at=now)
            active_documents_under_deleted_folders.update(is_deleted=True, deleted_at=now)

        self.stdout.write(f"Timezone-aware rows updated: {updated}")
        self.stdout.write(f"Deleted folders missing deleted_at: {folder_count}")
        self.stdout.write(f"Deleted documents missing deleted_at: {document_count}")
        self.stdout.write(f"Active documents under deleted folders: {orphan_count}")
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run only. No database changes were saved."))
        else:
            self.stdout.write(self.style.SUCCESS("Timezone normalization complete."))
