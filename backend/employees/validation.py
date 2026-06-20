from config.employee_number import normalize_employee_number

from .permissions import can_change_employee_number
from .references import get_reference_count_for_employee

EMPLOYEE_NUMBER_TAGGED_LOCK_MESSAGE = (
    "Employee Number cannot be modified because this requisitioner is referenced by existing documents."
)
EMPLOYEE_NUMBER_OVERRIDE_REASON_REQUIRED = (
    "A reason is required to override the employee number lock."
)


def normalized_employee_number(value):
    return normalize_employee_number(value or "") or None


def employee_number_changed(existing_number, new_number):
    return normalized_employee_number(existing_number) != normalized_employee_number(new_number)


def format_employee_number_for_audit(value):
    return normalized_employee_number(value) or "No Emp No. Provided"


def get_employee_number_edit_state(employee, user=None):
    tagged_count = get_reference_count_for_employee(employee)
    can_change = tagged_count == 0
    block_reason = None if can_change else EMPLOYEE_NUMBER_TAGGED_LOCK_MESSAGE
    return {
        "can_change": can_change,
        "block_reason": block_reason,
        "tagged_count": tagged_count,
    }


def can_admin_override_employee_number_lock(user):
    return getattr(user, "role", None) == "admin"


def assert_can_update_employee_number(user, instance, new_number, *, override_reason=None):
    if not instance:
        return
    if not employee_number_changed(instance.employee_number, new_number):
        return
    if not can_change_employee_number(user):
        from rest_framework.exceptions import ValidationError

        raise ValidationError(
            {"employeeNumber": "Only Admin or Dept Head can change the employee number after save."}
        )

    tagged_count = get_reference_count_for_employee(instance)
    if tagged_count == 0:
        return

    override_reason = (override_reason or "").strip()
    if can_admin_override_employee_number_lock(user) and override_reason:
        return

    from rest_framework.exceptions import ValidationError

    raise ValidationError({"employeeNumber": EMPLOYEE_NUMBER_TAGGED_LOCK_MESSAGE})


def build_employee_number_audit_details(
    *,
    employee_id,
    old_number,
    new_number,
    user_email,
    override_reason=None,
):
    parts = [
        f"Requisitioner ID: {employee_id}",
        f"Old: {format_employee_number_for_audit(old_number)}",
        f"New: {format_employee_number_for_audit(new_number)}",
        f"User: {user_email or 'system'}",
    ]
    if override_reason:
        parts.append(f"Reason: {override_reason.strip()}")
    return " | ".join(parts)
