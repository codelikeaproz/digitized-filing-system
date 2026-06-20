"""Institutional employee number validation (Letter-Year-Code)."""
import re

EMPLOYEE_NUMBER_PATTERN = re.compile(r"^[A-Z]-\d{4}-[A-Z0-9]+$")
LEGACY_NUMERIC_PATTERN = re.compile(r"^\d+$")

EMPLOYEE_NUMBER_PLACEHOLDER = "Example: D-2122-GCM"
EMPLOYEE_NUMBER_HELPER_TEXT = "Format: Letter-Year-Code"
EMPLOYEE_NUMBER_REQUIRED_ERROR = "Employee number is required."
EMPLOYEE_NUMBER_FORMAT_ERROR = (
    "Employee number must follow the format Letter-Year-Code (e.g. D-2122-GCM)."
)
EMPLOYEE_NUMBER_LEGACY_ERROR = "Employee number must contain digits only."


def normalize_employee_number(value):
    return (value or "").strip().upper()


def is_legacy_numeric_employee_number(value):
    cleaned = normalize_employee_number(value)
    return bool(cleaned) and LEGACY_NUMERIC_PATTERN.fullmatch(cleaned)


def validate_employee_number_value(value, *, required=True, allow_legacy=False):
    cleaned = normalize_employee_number(value)
    if not cleaned:
        if required:
            return EMPLOYEE_NUMBER_REQUIRED_ERROR
        return None

    if EMPLOYEE_NUMBER_PATTERN.fullmatch(cleaned):
        return None

    if allow_legacy and is_legacy_numeric_employee_number(cleaned):
        return None

    return EMPLOYEE_NUMBER_FORMAT_ERROR


def validate_optional_employee_number_value(value, *, allow_legacy=False):
    return validate_employee_number_value(value, required=False, allow_legacy=allow_legacy)
