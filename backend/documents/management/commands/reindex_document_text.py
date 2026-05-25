from django.core.management.base import BaseCommand

from ai.services.extraction_service import index_document_text
from documents.models import Document


class Command(BaseCommand):
    help = "Re-index uploaded PDF text for chatbot search, including OCR fallback for scanned PDFs."

    def add_arguments(self, parser):
        parser.add_argument("--document-id", type=int, help="Re-index one document by id.")
        parser.add_argument("--limit", type=int, help="Maximum number of documents to re-index.")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-index documents even if they already have extracted text.",
        )

    def handle(self, *args, **options):
        queryset = Document.objects.filter(is_deleted=False).exclude(file="")

        document_id = options.get("document_id")
        if document_id:
            queryset = queryset.filter(pk=document_id)

        if not options.get("force"):
            queryset = queryset.filter(extracted_text="")

        queryset = queryset.order_by("id")
        limit = options.get("limit")
        if limit:
            queryset = queryset[:limit]

        total = 0
        indexed = 0
        for document in queryset:
            total += 1
            self.stdout.write(f"Indexing document #{document.pk}: {document.title}")
            index_document_text(document)
            document.refresh_from_db(fields=["extracted_text"])
            if document.extracted_text:
                indexed += 1

        self.stdout.write(self.style.SUCCESS(f"Processed {total} document(s); indexed text found for {indexed}."))
