from django.core.management.base import BaseCommand

from documents.models import Document
from documents.services import build_folder_path_map


class Command(BaseCommand):
    help = "Recompute stored file_path for all documents from their current folder hierarchy."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report how many rows would change without saving.",
        )

    def handle(self, *args, **options):
        documents = list(
            Document.objects.filter(folder_id__isnull=False).only("id", "folder_id", "file_path")
        )
        folder_ids = {document.folder_id for document in documents}
        path_map = build_folder_path_map(folder_ids)

        to_update = []
        for document in documents:
            new_path = path_map.get(document.folder_id, "")
            if document.file_path != new_path:
                document.file_path = new_path
                to_update.append(document)

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"Dry run: {len(to_update)} document(s) would be updated."))
            return

        if to_update:
            Document.objects.bulk_update(to_update, ["file_path"], batch_size=500)

        self.stdout.write(self.style.SUCCESS(f"Updated {len(to_update)} document(s)."))
