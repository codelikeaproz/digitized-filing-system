"""
Auto-generated document codes: {CategoryCode}-{Year}-{Sequence}.

Sequence counters are shared globally per (category_code, current_year).
"""
import re

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Category, Document, DocumentSequence

CATEGORY_CODE_PATTERN = re.compile(r"^[A-Z0-9]+$")
GENERATED_DOCUMENT_CODE_PATTERN = re.compile(r"^([A-Z0-9]+)-(\d{4})-(\d{6})$")
MAX_GENERATION_RETRIES = 5


def normalize_category_code(value):
    code = re.sub(r"[^A-Z0-9]", "", (value or "").strip().upper())
    if not code:
        raise ValidationError("Category Code is required.")
    if len(code) > 10:
        raise ValidationError("Category Code must be at most 10 characters.")
    if not CATEGORY_CODE_PATTERN.fullmatch(code):
        raise ValidationError("Category Code can contain uppercase letters and numbers only.")
    return code


def _base_category_code(name):
    letters = re.sub(r"[^A-Za-z0-9]", "", (name or "").upper())
    if not letters:
        return "CAT"
    return letters[:3]


def derive_category_code(name, org_unit_id=None, *, exclude_category_id=None):
    base = _base_category_code(name)
    candidate = base
    suffix = 1
    while True:
        queryset = Category.objects.filter(code__iexact=candidate)
        if org_unit_id:
            queryset = queryset.filter(org_unit_id=org_unit_id)
        else:
            queryset = queryset.filter(org_unit__isnull=True)
        if exclude_category_id:
            queryset = queryset.exclude(pk=exclude_category_id)
        if not queryset.exists():
            return candidate
        suffix += 1
        candidate = f"{base}{suffix}"[:10]


def format_document_code(category_code, year, sequence):
    return f"{category_code}-{year}-{sequence:06d}"


def _next_sequence_number(category_code, year):
    seq = DocumentSequence.objects.filter(category_code=category_code, current_year=year).first()
    return (seq.current_number + 1) if seq else 1


def preview_next_document_code(category):
    if not category or not (category.code or "").strip():
        raise ValidationError("Category must have a code before documents can be uploaded.")
    category_code = normalize_category_code(category.code)
    year = timezone.now().year
    return format_document_code(category_code, year, _next_sequence_number(category_code, year))


def _lock_sequence_row(category_code, year):
    seq = DocumentSequence.objects.select_for_update().filter(
        category_code=category_code,
        current_year=year,
    ).first()
    if seq:
        return seq
    try:
        return DocumentSequence.objects.create(
            category_code=category_code,
            current_year=year,
            current_number=0,
        )
    except IntegrityError:
        return DocumentSequence.objects.select_for_update().get(
            category_code=category_code,
            current_year=year,
        )


def generate_document_code(category):
    if not category or not (category.code or "").strip():
        raise ValidationError("Category must have a code before documents can be uploaded.")
    category_code = normalize_category_code(category.code)
    year = timezone.now().year

    for _attempt in range(MAX_GENERATION_RETRIES):
        with transaction.atomic():
            seq = _lock_sequence_row(category_code, year)
            seq = DocumentSequence.objects.select_for_update().get(pk=seq.pk)
            seq.current_number += 1
            seq.save(update_fields=["current_number", "updated_at"])
            code = format_document_code(category_code, year, seq.current_number)
            if Document.objects.filter(code__iexact=code).exists():
                continue
            return code

    raise ValidationError("Unable to generate a unique document code. Please try again.")
