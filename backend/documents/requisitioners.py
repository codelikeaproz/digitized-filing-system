import json
import re

from rest_framework.exceptions import ValidationError

from .models import Document, DocumentRequisitioner

EMPLOYEE_NUMBER_PATTERN = re.compile(r"^\d+$")
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


def format_requisitioners_display(requisitioners):
    parts = []
    for item in requisitioners:
        employee_number = getattr(item, "employee_number", None) or item.get("employeeNumber", "")
        if hasattr(item, "get_full_name"):
            full_name = item.get_full_name()
        else:
            full_name = build_requisitioner_full_name(
                item.get("first_name", item.get("firstName", "")),
                item.get("last_name", item.get("lastName", "")),
                item.get("suffix", ""),
            )
            if not full_name:
                full_name = str(item.get("fullName", item.get("full_name", "")) or "").strip()
        employee_number = str(employee_number or "").strip()
        full_name = str(full_name or "").strip()
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


def normalize_requisitioner_item(raw_item):
    if not isinstance(raw_item, dict):
        raise ValidationError("Each requisitioner must be an object.")

    employee_number = str(raw_item.get("employeeNumber", raw_item.get("employee_number", "")) or "").strip()
    first_name = normalize_name_part(raw_item.get("firstName", raw_item.get("first_name", "")))
    last_name = normalize_name_part(raw_item.get("lastName", raw_item.get("last_name", "")))
    suffix = (raw_item.get("suffix") or "").strip()

    if not first_name and not last_name:
        legacy_full_name = raw_item.get("fullName", raw_item.get("full_name", ""))
        first_name, last_name, parsed_suffix = split_full_name(legacy_full_name)
        if not suffix:
            suffix = parsed_suffix

    if not employee_number:
        raise ValidationError("Employee Number is required for each requisitioner.")
    if not EMPLOYEE_NUMBER_PATTERN.fullmatch(employee_number):
        raise ValidationError("Employee Number must contain digits only.")
    if not first_name:
        raise ValidationError("First Name is required for each requisitioner.")
    if not last_name:
        raise ValidationError("Last Name is required for each requisitioner.")
    if suffix and suffix not in ALLOWED_NAME_SUFFIXES:
        raise ValidationError("Select a valid name suffix.")

    return {
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
    for raw_item in items:
        item = normalize_requisitioner_item(raw_item)
        if item["employee_number"] in seen_numbers:
            raise ValidationError(
                "Duplicate Employee Numbers are not allowed within the same document."
            )
        seen_numbers.add(item["employee_number"])
        normalized.append(item)
    return normalized


def sync_document_requisitioners(document, items):
    validated = validate_requisitioners_list(items)
    document.requisitioners.all().delete()
    DocumentRequisitioner.objects.bulk_create(
        [
            DocumentRequisitioner(
                document=document,
                employee_number=item["employee_number"],
                first_name=item["first_name"],
                last_name=item["last_name"],
                suffix=item["suffix"],
            )
            for item in validated
        ]
    )
    display_value = format_requisitioners_display(validated) or None
    if document.requestor != display_value:
        document.requestor = display_value
        document.save(update_fields=["requestor", "updated_at"])
    return validated
