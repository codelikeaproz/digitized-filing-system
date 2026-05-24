"""
Document and folder access control helpers.

Centralizes OrgUnit scoping and role checks used by document views,
recycle bin, uploads, and scanner job endpoints.

Rules summary:
    admin     -> global access (callers skip queryset filters)
    dept_head -> own OrgUnit + child OrgUnits
    staff     -> own OrgUnit only; no recycle bin; no document delete
"""

import secrets

from django.conf import settings
from rest_framework.exceptions import PermissionDenied


def org_unit_scope_ids(user):
    """
    Return OrgUnit primary keys visible to the user for document scoping.

    Admin callers should not rely on this helper — admin views skip filtering.
    Dept Head receives own unit plus all descendant units.
    """
    org_unit = getattr(user, "org_unit", None)
    if not org_unit:
        return []
    if getattr(user, "role", None) == "dept_head":
        return [org_unit.id, *[child.id for child in org_unit.get_all_children()]]
    return [org_unit.id]


def assert_recycle_bin_access(user, folder_or_document):
    """
    Recycle bin is limited to Admin (global) and Dept Head (scoped org tree).
    Staff users are always denied.
    """
    if getattr(user, "role", None) == "admin":
        return
    if getattr(user, "role", None) != "dept_head":
        raise PermissionDenied("Staff do not have Recycle Bin access.")

    folder = getattr(folder_or_document, "folder", folder_or_document)
    if folder.org_unit_id not in org_unit_scope_ids(user):
        raise PermissionDenied("You do not have access to this recycle bin item.")


def assert_scanner_bridge(request):
    """Validate Scanner Bridge token from X-Scanner-Token header."""
    expected_token = settings.SCANNER_BRIDGE_TOKEN
    received_token = request.headers.get("X-Scanner-Token", "")
    if not expected_token or not secrets.compare_digest(received_token, expected_token):
        raise PermissionDenied("Invalid scanner bridge token.")


def assert_folder_write_access(user, folder):
    """
    Allow writes when the folder belongs to the user's OrgUnit scope.
    Admin bypasses all checks.
    """
    role = getattr(user, "role", None)
    if role == "admin":
        return

    org_unit = getattr(user, "org_unit", None)
    if not org_unit:
        raise PermissionDenied("You do not have access to this folder.")

    if role == "dept_head":
        if folder.org_unit_id in org_unit_scope_ids(user):
            return
        raise PermissionDenied("You do not have access to this folder.")

    if role == "staff":
        if folder.org_unit_id == org_unit.id:
            return
        raise PermissionDenied("You do not have access to this folder.")

    raise PermissionDenied("You do not have access to this folder.")


def assert_document_write_access(user, document):
    """Same OrgUnit rules as folder access, applied via document.folder."""
    role = getattr(user, "role", None)
    if role == "admin":
        return

    org_unit = getattr(user, "org_unit", None)
    if not org_unit:
        raise PermissionDenied("You do not have access to this document.")

    if role == "dept_head":
        if document.folder.org_unit_id in org_unit_scope_ids(user):
            return
        raise PermissionDenied("You do not have access to this document.")

    if role == "staff":
        if document.folder.org_unit_id == org_unit.id:
            return
        raise PermissionDenied("You do not have access to this document.")

    raise PermissionDenied("You do not have access to this document.")


def assert_category_delete_access(user, category):
    """Category delete must stay within the user's OrgUnit scope."""
    role = getattr(user, "role", None)
    if role == "admin":
        return

    org_unit = getattr(user, "org_unit", None)
    if not org_unit or not category.org_unit_id:
        raise PermissionDenied("You do not have access to this category.")

    if role == "dept_head":
        if category.org_unit_id in org_unit_scope_ids(user):
            return
        raise PermissionDenied("You do not have access to this category.")

    if role == "staff":
        if category.org_unit_id == org_unit.id:
            return
        raise PermissionDenied("You do not have access to this category.")

    raise PermissionDenied("You do not have access to this category.")
