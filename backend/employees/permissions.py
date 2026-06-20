from rest_framework.exceptions import PermissionDenied

from auditlogs.models import log_audit


def _role(user):
    return getattr(user, "role", None)


def can_access_requisitioners_directory(user):
    return _role(user) in {"admin", "dept_head"}


def can_manage_requisitioners(user):
    return _role(user) == "admin"


def can_search_requisitioners_for_documents(user):
    return bool(user and getattr(user, "is_authenticated", False))


def can_change_employee_number(user):
    return _role(user) in {"admin", "dept_head"}


def log_directory_access_denied(user, request, resource):
    org_unit = getattr(user, "org_unit", None)
    org_name = org_unit.name if org_unit else "Global Access"
    email = getattr(user, "email", "unknown")
    role = _role(user) or "unknown"
    log_audit(
        user,
        "REQUISITIONER_DIRECTORY_ACCESS_DENIED",
        f"Denied {resource} access for {email} ({role}, {org_name})",
        target_type="Employee",
        target_name=resource,
        target_org_unit=org_name if org_unit else None,
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
    )


def assert_directory_read(user, *, search, request=None, resource="Requisitioners Directory"):
    if can_access_requisitioners_directory(user):
        return
    if can_search_requisitioners_for_documents(user) and (search or "").strip():
        return
    if request is not None:
        log_directory_access_denied(user, request, resource)
    raise PermissionDenied("You do not have permission to access the Requisitioners Directory.")


def assert_directory_admin(user):
    if not can_manage_requisitioners(user):
        raise PermissionDenied("Only administrators can manage the Requisitioners Directory.")


def assert_can_search_requisitioners(user, *, search, request=None):
    assert_directory_read(user, search=search, request=request)


def assert_can_manage_requisitioners(user):
    assert_directory_admin(user)


def assert_can_change_employee_number(user):
    if not can_change_employee_number(user):
        raise PermissionDenied("Only Admin or Dept Head can change the employee number after save.")


def assert_admin_only(user):
    if _role(user) != "admin":
        raise PermissionDenied("Only administrators can perform this action.")
