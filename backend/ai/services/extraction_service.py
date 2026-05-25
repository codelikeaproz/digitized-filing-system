import hashlib
import logging
from pathlib import Path
import re

from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)


def extracted_text_limit():
    return getattr(settings, "DOCUMENT_TEXT_INDEX_CHAR_LIMIT", 250_000)


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


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
            if sum(len(part) for part in parts) >= extracted_text_limit():
                break
        return "\n".join(parts).strip()[:extracted_text_limit()]
    except Exception:
        logger.exception("Failed to extract PDF text for document %s", document.pk)
        return ""


def extract_pdf_text_with_ocr(document):
    if not getattr(settings, "OCR_ENABLED", True):
        return ""
    if not document.file:
        return ""

    file_path = Path(document.file.path)
    if not file_path.exists():
        return ""

    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        logger.warning("OCR dependencies are not installed; skipping OCR for document %s", document.pk)
        return ""

    try:
        max_pages = getattr(settings, "OCR_MAX_PAGES", 10)
        pages = convert_from_path(
            str(file_path),
            dpi=getattr(settings, "OCR_DPI", 200),
            first_page=1,
            last_page=max_pages,
        )
        parts = []
        language = getattr(settings, "OCR_LANGUAGE", "eng")
        for page in pages:
            text = pytesseract.image_to_string(page, lang=language) or ""
            if text.strip():
                parts.append(text)
            if sum(len(part) for part in parts) >= extracted_text_limit():
                break
        return "\n".join(parts).strip()[:extracted_text_limit()]
    except Exception:
        logger.exception("Failed to OCR PDF text for document %s", document.pk)
        return ""


def generate_document_summary(text):
    normalized = normalize_text(text)
    if not normalized:
        return ""

    max_chars = getattr(settings, "AI_SUMMARY_MAX_CHARS", 1200)
    max_sentences = getattr(settings, "AI_SUMMARY_MAX_SENTENCES", 6)
    sentences = re.split(r"(?<=[.!?])\s+", normalized)

    summary_parts = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        next_summary = " ".join([*summary_parts, sentence]).strip()
        if summary_parts and len(next_summary) > max_chars:
            break
        summary_parts.append(sentence)
        if len(summary_parts) >= max_sentences:
            break

    summary = " ".join(summary_parts).strip()
    if not summary:
        summary = normalized[:max_chars].strip()
    elif len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(" ", 1)[0].strip()

    return summary


def index_document_text(document):
    if not document.file:
        return document

    file_path = Path(document.file.path)
    if not file_path.exists():
        return document

    document.content_hash = compute_file_hash(file_path)
    extracted_text = extract_pdf_text(document)
    min_text_length = getattr(settings, "OCR_MIN_TEXT_LENGTH", 50)
    if len(extracted_text.strip()) < min_text_length:
        ocr_text = extract_pdf_text_with_ocr(document)
        if ocr_text:
            extracted_text = ocr_text
    document.extracted_text = extracted_text
    document.ai_summary = generate_document_summary(extracted_text)
    document.last_indexed_at = timezone.now()
    document.save(update_fields=["content_hash", "extracted_text", "ai_summary", "last_indexed_at", "updated_at"])
    return document
