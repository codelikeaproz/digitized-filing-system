import hashlib
import logging
from pathlib import Path

from django.utils import timezone


logger = logging.getLogger(__name__)
MAX_EXTRACTED_TEXT_LENGTH = 120_000


def compute_file_hash(file_path):
    digest = hashlib.sha256()
    with open(file_path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_pdf_text(document):
    if not document.file:
        return ""

    file_path = Path(document.file.path)
    if not file_path.exists():
        return ""

    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning("pypdf is not installed; skipping text extraction for document %s", document.pk)
        return ""

    try:
        reader = PdfReader(str(file_path))
        parts = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text:
                parts.append(text)
            if sum(len(part) for part in parts) >= MAX_EXTRACTED_TEXT_LENGTH:
                break
        return "\n".join(parts).strip()[:MAX_EXTRACTED_TEXT_LENGTH]
    except Exception:
        logger.exception("Failed to extract PDF text for document %s", document.pk)
        return ""


def index_document_text(document):
    if not document.file:
        return document

    file_path = Path(document.file.path)
    if not file_path.exists():
        return document

    document.content_hash = compute_file_hash(file_path)
    document.extracted_text = extract_pdf_text(document)
    document.last_indexed_at = timezone.now()
    document.save(update_fields=["content_hash", "extracted_text", "last_indexed_at", "updated_at"])
    return document
