"""Manual document code validation (no auto-generation)."""
import re

from rest_framework import serializers

from .models import Document

DOCUMENT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")


def normalize_document_code(value):
    code = (value or "").strip().upper()
    if not code:
        raise serializers.ValidationError("Document Code is required.")
    if not DOCUMENT_CODE_PATTERN.fullmatch(code):
        raise serializers.ValidationError("Document Code can contain letters, numbers, and hyphens only.")
    return code


def ensure_unique_document_code(code, *, document_id=None):
    queryset = Document.objects.filter(code__iexact=code)
    if document_id:
        queryset = queryset.exclude(pk=document_id)
    if queryset.exists():
        raise serializers.ValidationError("Document Code is already used.")
