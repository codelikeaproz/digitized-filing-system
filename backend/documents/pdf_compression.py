"""
Lossless PDF stream compression for manual uploads.

Uses pypdf to compress content streams and deduplicate objects.
Falls back to the original file when compression fails or does not reduce size.
"""
import io
import logging

from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def compress_pdf_upload(uploaded_file):
    """
    Return a smaller ContentFile when compression helps, otherwise the original upload.
  """
    if not getattr(settings, "PDF_COMPRESSION_ENABLED", True):
        return uploaded_file

    original_size = getattr(uploaded_file, "size", 0) or 0
    if original_size <= 0:
        return uploaded_file

    try:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(uploaded_file)
        writer = PdfWriter()

        for page in reader.pages:
            page.compress_content_streams()
            writer.add_page(page)

        if reader.metadata:
            writer.add_metadata(reader.metadata)

        writer.compress_identical_objects(remove_identicals=True)

        buffer = io.BytesIO()
        writer.write(buffer)
        compressed_bytes = buffer.getvalue()

        if len(compressed_bytes) >= original_size:
            uploaded_file.seek(0)
            return uploaded_file

        if not compressed_bytes.startswith(b"%PDF"):
            uploaded_file.seek(0)
            return uploaded_file

        saved_bytes = original_size - len(compressed_bytes)
        logger.info(
            "PDF compressed: %s (%s bytes -> %s bytes, saved %s bytes)",
            getattr(uploaded_file, "name", "upload"),
            original_size,
            len(compressed_bytes),
            saved_bytes,
        )
        return ContentFile(compressed_bytes, name=uploaded_file.name)
    except Exception as exc:
        logger.warning("PDF compression skipped for %s: %s", getattr(uploaded_file, "name", "upload"), exc)
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        return uploaded_file
