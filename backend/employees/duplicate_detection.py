"""Duplicate detection for Requisitioners Directory and manual document tags."""
from django.db.models import Q

from config.employee_number import normalize_employee_number
from documents.requisitioners import normalize_name_part

from .models import Employee

EMPLOYEE_NUMBER_EXISTS_MESSAGE = (
    "Employee Number already exists. Please select the existing requisitioner."
)
SIMILAR_NAME_EXISTS_MESSAGE = (
    "A requisitioner with a similar name already exists. "
    "Please select the existing requisitioner from the directory."
)


def employee_to_match_dict(employee):
    return {
        "id": str(employee.id),
        "employeeNumber": employee.employee_number or "",
        "firstName": employee.first_name,
        "lastName": employee.last_name,
        "suffix": employee.suffix or "",
        "fullName": employee.get_full_name(),
    }


def find_employee_by_number(employee_number, *, exclude_id=None):
    cleaned = normalize_employee_number(employee_number)
    if not cleaned:
        return None
    queryset = Employee.objects.filter(employee_number__iexact=cleaned, is_active=True)
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    return queryset.first()


def find_employees_by_exact_name(first_name, last_name, suffix="", *, exclude_id=None):
    queryset = Employee.objects.filter(
        is_active=True,
        first_name__iexact=normalize_name_part(first_name),
        last_name__iexact=normalize_name_part(last_name),
        suffix=suffix or "",
    )
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    return list(queryset.order_by("last_name", "first_name", "id"))


def find_similar_employees(first_name, last_name, suffix="", *, exclude_id=None):
    """Return potential duplicate employees (exact normalized name match)."""
    return find_employees_by_exact_name(first_name, last_name, suffix, exclude_id=exclude_id)


def check_manual_requisitioner_duplicates(
    *,
    employee_number=None,
    first_name="",
    last_name="",
    suffix="",
    exclude_employee_id=None,
):
    """
    Check whether a manual tag would duplicate directory data.
    Returns dict with keys: blocked (bool), message (str|None), matches (list).
    """
    if employee_number:
        existing = find_employee_by_number(employee_number, exclude_id=exclude_employee_id)
        if existing:
            return {
                "blocked": True,
                "message": EMPLOYEE_NUMBER_EXISTS_MESSAGE,
                "matches": [employee_to_match_dict(existing)],
            }

    similar = find_similar_employees(
        first_name,
        last_name,
        suffix,
        exclude_id=exclude_employee_id,
    )
    if similar:
        return {
            "blocked": True,
            "message": SIMILAR_NAME_EXISTS_MESSAGE,
            "matches": [employee_to_match_dict(employee) for employee in similar],
        }

    return {"blocked": False, "message": None, "matches": []}
