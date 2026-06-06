from rest_framework.exceptions import PermissionDenied

from auditlogs.models import log_audit


def assert_backup_access(user, *, backup_type=None, ip_address=None):
    """Allow backup downloads for admin role only."""
    if not user or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")

    if getattr(user, "role", None) != "admin":
        if backup_type:
            log_audit(
                user,
                "BACKUP_ACCESS_DENIED",
                f"Unauthorized backup attempt: {backup_type}",
                target_type="Backup",
                target_name=backup_type,
                target_org_unit=getattr(getattr(user, "org_unit", None), "name", None),
                ip_address=ip_address,
            )
        raise PermissionDenied("Only administrators can access backups.")
