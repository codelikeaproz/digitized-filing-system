import json
import re

from rest_framework.exceptions import ValidationError

from .models import Document, DocumentRequisitioner

from config.employee_number import (
    normalize_employee_number,
    validate_optional_employee_number_value,
)
ALLOWED_NAME_SUFFIXES = {"", "Jr.", "Sr.", "I", "II", "III", "IV", "V"}


def normalize_name_part(value):
    cleaned = (value or "").strip()
    if not cleaned:
        return ""

    def capitalize_part(part):
        return part[:1].upper() + part[1:].lower() if part else ""

    words = []
    for word in cleaned.split():
        words.append("-".join(capitalize_part(piece) for piece in word.split("-") if piece is not None))
    return " ".join(words)


def split_full_name(full_name):
    parts = normalize_name_part(full_name).split()
    if not parts:
        return "", "", ""

    suffix = ""
    if len(parts) > 1 and parts[-1] in ALLOWED_NAME_SUFFIXES:
        suffix = parts[-1]
        parts = parts[:-1]

    if not parts:
        return "", "", suffix
    if len(parts) == 1:
        return parts[0], "", suffix
    return parts[0], " ".join(parts[1:]), suffix


def build_requisitioner_full_name(first_name="", last_name="", suffix=""):
    parts = [normalize_name_part(first_name), normalize_name_part(last_name)]
    cleaned_suffix = (suffix or "").strip()
    if cleaned_suffix:
        parts.append(cleaned_suffix)
    return " ".join(part for part in parts if part).strip()


def _requisitioner_employee_number(item):
    if isinstance(item, dict):
        return str(item.get("employeeNumber") or item.get("employee_number") or "").strip()
    return str(getattr(item, "employee_number", None) or "").strip()


def _requisitioner_full_name(item):
    if hasattr(item, "get_full_name"):
        full_name = item.get_full_name()
        if full_name:
            return str(full_name).strip()
    if isinstance(item, dict):
        full_name = build_requisitioner_full_name(
            item.get("first_name", item.get("firstName", "")),
            item.get("last_name", item.get("lastName", "")),
            item.get("suffix", ""),
        )
        if full_name:
            return full_name
        return str(item.get("fullName", item.get("full_name", "")) or "").strip()
    return build_requisitioner_full_name(
        getattr(item, "first_name", ""),
        getattr(item, "last_name", ""),
        getattr(item, "suffix", ""),
    )


def format_requisitioners_display(requisitioners):
    parts = []
    for item in requisitioners:
        employee_number = _requisitioner_employee_number(item)
        full_name = _requisitioner_full_name(item)
        if employee_number and full_name:
            parts.append(f"{employee_number} - {full_name}")
        elif full_name:
            parts.append(full_name)
    return ", ".join(parts)


def parse_requisitioners(value):
    if value in (None, "", []):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValidationError("Requisitioners must be a valid JSON array.") from exc
        if not isinstance(parsed, list):
            raise ValidationError("Requisitioners must be a JSON array.")
        return parsed
    raise ValidationError("Requisitioners must be a JSON array.")


def _parse_employee_id(raw_item):
    raw_id = raw_item.get("employeeId", raw_item.get("employee_id"))
    if raw_id in (None, ""):
        return None
    return raw_id


def _parse_source(raw_item, employee_id):
    raw_source = (raw_item.get("source") or "").strip().lower()
    if raw_source in {DocumentRequisitioner.SOURCE_DIRECTORY, DocumentRequisitioner.SOURCE_MANUAL}:
        return raw_source
    if employee_id:
        return DocumentRequisitioner.SOURCE_DIRECTORY
    return DocumentRequisitioner.SOURCE_MANUAL


def normalize_requisitioner_item(raw_item):
    if not isinstance(raw_item, dict):
        raise ValidationError("Each requisitioner must be an object.")

    employee_id = _parse_employee_id(raw_item)
    source = _parse_source(raw_item, employee_id)

    employee_number = normalize_employee_number(
        str(raw_item.get("employeeNumber", raw_item.get("employee_number", "")) or "")
    )
    if not employee_number:
        employee_number = None
    first_name = normalize_name_part(raw_item.get("firstName", raw_item.get("first_name", "")))
    last_name = normalize_name_part(raw_item.get("lastName", raw_item.get("last_name", "")))
    suffix = (raw_item.get("suffix") or "").strip()

    if not first_name and not last_name:
        legacy_full_name = raw_item.get("fullName", raw_item.get("full_name", ""))
        first_name, last_name, parsed_suffix = split_full_name(legacy_full_name)
        if not suffix:
            suffix = parsed_suffix

    if source == DocumentRequisitioner.SOURCE_DIRECTORY:
        if not employee_id:
            raise ValidationError("Directory requisitioners must include employeeId.")
        from employees.models import Employee

        employee = Employee.objects.filter(pk=employee_id, is_active=True).first()
        if not employee:
            raise ValidationError("Selected requisitioner no longer exists in the directory.")
        employee_number = employee.employee_number
        first_name = employee.first_name
        last_name = employee.last_name
        suffix = employee.suffix or ""
    elif employee_number:
        error = validate_optional_employee_number_value(employee_number, allow_legacy=True)
        if error:
            raise ValidationError(error)

    if not first_name:
        raise ValidationError("First Name is required for each requisitioner.")
    if not last_name:
        raise ValidationError("Last Name is required for each requisitioner.")
    if suffix and suffix not in ALLOWED_NAME_SUFFIXES:
        raise ValidationError("Select a valid name suffix.")

    return {
        "employee_id": employee_id,
        "source": source,
        "employee_number": employee_number,
        "first_name": first_name,
        "last_name": last_name,
        "suffix": suffix,
    }


def validate_requisitioners_list(items, *, require_at_least_one=True):
    if not items:
        if require_at_least_one:
            raise ValidationError("At least one requisitioner is required.")
        return []

    normalized = []
    seen_numbers = set()
    seen_employee_ids = set()
    for raw_item in items:
        item = normalize_requisitioner_item(raw_item)
        employee_number = item["employee_number"]
        employee_id = item.get("employee_id")

        if employee_id:
            if employee_id in seen_employee_ids:
                raise ValidationError("Duplicate requisitioners are not allowed on the same document.")
            seen_employee_ids.add(employee_id)

        if employee_number:
            if employee_number in seen_numbers:
                raise ValidationError(
                    "Duplicate Employee Numbers are not allowed within the same document."
                )
            seen_numbers.add(employee_number)
        normalized.append(item)
    return normalized


def sync_document_requisitioners(document, items, *, user=None):
    del user
    from employees.sync import link_document_requisitioners

    validated = validate_requisitioners_list(items)
    linked = link_document_requisitioners(validated, document=document)

    document.requisitioners.all().delete()
    DocumentRequisitioner.objects.bulk_create(
        [
            DocumentRequisitioner(
                document=document,
                employee_id=item.get("employee_id"),
                source=item.get("source") or DocumentRequisitioner.SOURCE_MANUAL,
                employee_number=item["employee_number"],
                first_name=item["first_name"],
                last_name=item["last_name"],
                suffix=item["suffix"],
            )
            for item in linked
        ]
    )
    display_value = format_requisitioners_display(linked) or None
    if document.requestor != display_value:
        document.requestor = display_value
        document.save(update_fields=["requestor", "updated_at"])
    return linked
