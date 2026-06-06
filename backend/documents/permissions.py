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
    return get_accessible_org_unit_ids(user)


def get_accessible_org_unit_ids(user):
    """Alias for org_unit_scope_ids — IDs the user may read documents from."""
    org_unit = getattr(user, "org_unit", None)
    if not org_unit:
        return []
    if getattr(user, "role", None) == "dept_head":
        return [org_unit.id, *org_unit.get_descendant_ids()]
    return [org_unit.id]


def get_scoped_org_units_queryset(user):
    """OrgUnit queryset limited to the user's accessible hierarchy."""
    from orgunits.models import OrgUnit

    queryset = OrgUnit.objects.filter(is_deleted=False)
    role = getattr(user, "role", None)
    if role == "admin":
        return queryset
    scope_ids = get_accessible_org_unit_ids(user)
    if not scope_ids:
        return queryset.none()
    return queryset.filter(id__in=scope_ids)


def assert_org_unit_in_scope(user, org_unit_id):
    """Raise PermissionDenied when the Office Unit is outside the user's scope."""
    if getattr(user, "role", None) == "admin":
        return
    if org_unit_id is None:
        raise PermissionDenied("Office Unit is required.")
    try:
        normalized_id = int(org_unit_id)
    except (TypeError, ValueError) as exc:
        raise PermissionDenied("Invalid Office Unit.") from exc
    if normalized_id not in get_accessible_org_unit_ids(user):
        raise PermissionDenied("You do not have access to this Office Unit.")


def assert_folder_in_scope(user, folder):
    """Raise PermissionDenied when the folder's Office Unit is outside scope."""
    if getattr(user, "role", None) == "admin":
        return
    if not folder or not folder.org_unit_id:
        raise PermissionDenied("You do not have access to this folder.")
    assert_org_unit_in_scope(user, folder.org_unit_id)


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


def assert_category_write_access(user, category):
    """Category update must stay within the user's OrgUnit scope."""
    assert_category_delete_access(user, category)


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
