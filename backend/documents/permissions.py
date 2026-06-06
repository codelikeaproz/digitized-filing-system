"""
Document and folder access control helpers.

Centralizes OrgUnit scoping and role checks used by document views,
recycle bin, and uploads.

Rules summary:
    admin     -> global access (callers skip queryset filters)
    dept_head -> own OrgUnit + child OrgUnits
    staff     -> own OrgUnit only; no recycle bin; no document delete
"""

from rest_framework.exceptions import PermissionDenied

from documents.models import Category


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


def scoped_categories_queryset(user):
    """Categories visible to the user (admin: all; dept_head/staff: scoped org units)."""
    queryset = Category.objects.all()
    role = getattr(user, "role", None)
    if role == "admin":
        return queryset

    org_unit = getattr(user, "org_unit", None)
    if not org_unit:
        return queryset.none()

    queryset = queryset.exclude(org_unit__isnull=True)
    if role == "dept_head":
        return queryset.filter(org_unit_id__in=org_unit_scope_ids(user))
    return queryset.filter(org_unit_id=org_unit.id)


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


def resolve_category_org_unit_for_create(user, requested_org_unit_id=None):
    """
    Resolve the Org Unit for a new category.

    Admin must pick an Org Unit (no global/unassigned categories via this flow).
    Staff and Dept Head are always scoped to their allowed Org Unit(s).
    """
    role = getattr(user, "role", None)
    if role == "admin":
        if not requested_org_unit_id:
            raise PermissionDenied("Org Unit is required when creating a category.")
        return int(requested_org_unit_id)

    org_unit = getattr(user, "org_unit", None)
    if not org_unit:
        raise PermissionDenied("Your account must be assigned to an Org Unit to create categories.")

    if not requested_org_unit_id:
        return org_unit.id

    try:
        requested_id = int(requested_org_unit_id)
    except (TypeError, ValueError) as exc:
        raise PermissionDenied("Invalid Org Unit.") from exc

    if role == "staff" and requested_id != org_unit.id:
        raise PermissionDenied("Staff can only create categories for their own Org Unit.")

    if role == "dept_head" and requested_id not in org_unit_scope_ids(user):
        raise PermissionDenied("Department Head can only create categories within their Org Unit scope.")

    return requested_id


def assert_document_edit_access(user, document):
    """Admin and Dept Head may edit document metadata; Staff may rename only."""
    role = getattr(user, "role", None)
    if role == "staff":
        raise PermissionDenied("Staff cannot edit document details.")
    assert_document_write_access(user, document)
