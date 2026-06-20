from django.db.models import Q
from rest_framework.exceptions import ValidationError

from config.employee_number import normalize_employee_number
from documents.models import DocumentRequisitioner
from documents.requisitioners import normalize_name_part

from .duplicate_detection import (
    EMPLOYEE_NUMBER_EXISTS_MESSAGE,
    SIMILAR_NAME_EXISTS_MESSAGE,
    check_manual_requisitioner_duplicates,
    find_employee_by_number,
)
from .models import Employee


def snapshot_from_employee(employee):
    return {
        "employee_id": employee.id,
        "employee_number": employee.employee_number,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "suffix": employee.suffix or "",
        "source": DocumentRequisitioner.SOURCE_DIRECTORY,
    }


def snapshot_from_manual_item(item):
    return {
        "employee_id": item.get("employee_id"),
        "employee_number": item.get("employee_number"),
        "first_name": item.get("first_name"),
        "last_name": item.get("last_name"),
        "suffix": item.get("suffix") or "",
        "source": DocumentRequisitioner.SOURCE_MANUAL,
    }


def _create_manual_employee(item):
    duplicate = check_manual_requisitioner_duplicates(
        employee_number=item.get("employee_number"),
        first_name=item.get("first_name"),
        last_name=item.get("last_name"),
        suffix=item.get("suffix") or "",
    )
    if duplicate["blocked"]:
        message = duplicate["message"] or EMPLOYEE_NUMBER_EXISTS_MESSAGE
        raise ValidationError(
            {
                "requisitioners": message,
                "similarEmployees": duplicate["matches"],
            }
        )

    return Employee.objects.create(
        employee_number=item.get("employee_number"),
        first_name=item.get("first_name"),
        last_name=item.get("last_name"),
        suffix=item.get("suffix") or "",
        is_active=True,
    )


def _resolve_directory_item(item):
    employee_id = item.get("employee_id")
    if not employee_id:
        raise ValidationError({"requisitioners": "Directory requisitioner is missing employeeId."})

    employee = Employee.objects.filter(pk=employee_id, is_active=True).first()
    if not employee:
        raise ValidationError({"requisitioners": "Selected requisitioner no longer exists in the directory."})

    return snapshot_from_employee(employee)


def _resolve_manual_item(item):
    employee_id = item.get("employee_id")
    if employee_id:
        employee = Employee.objects.filter(pk=employee_id, is_active=True).first()
        if not employee:
            raise ValidationError({"requisitioners": "Linked requisitioner no longer exists in the directory."})

        if item.get("employee_number"):
            duplicate = check_manual_requisitioner_duplicates(
                employee_number=item.get("employee_number"),
                first_name=item.get("first_name"),
                last_name=item.get("last_name"),
                suffix=item.get("suffix") or "",
                exclude_employee_id=employee.id,
            )
            if duplicate["blocked"]:
                raise ValidationError(
                    {
                        "requisitioners": duplicate["message"] or SIMILAR_NAME_EXISTS_MESSAGE,
                        "similarEmployees": duplicate["matches"],
                    }
                )

        resolved = snapshot_from_manual_item(item)
        resolved["employee_id"] = employee.id
        return resolved

    if item.get("employee_number"):
        existing = find_employee_by_number(item["employee_number"])
        if existing:
            raise ValidationError({"requisitioners": EMPLOYEE_NUMBER_EXISTS_MESSAGE})

    employee = _create_manual_employee(item)
    resolved = snapshot_from_employee(employee)
    resolved["source"] = DocumentRequisitioner.SOURCE_MANUAL
    return resolved


def link_document_requisitioners(requisitioners, *, document=None):
    """
    Resolve document requisitioner tags against the Requisitioners Directory master.

    Directory-linked tags refresh snapshots from Employee and never mutate master data.
    Manual tags create a new Employee only when no duplicate exists; later edits update
    the document snapshot only.
    """
    del document
    linked = []
    for item in requisitioners:
        source = item.get("source") or (
            DocumentRequisitioner.SOURCE_DIRECTORY
            if item.get("employee_id")
            else DocumentRequisitioner.SOURCE_MANUAL
        )
        if source == DocumentRequisitioner.SOURCE_DIRECTORY or item.get("employee_id"):
            linked.append(_resolve_directory_item(item))
        else:
            linked.append(_resolve_manual_item(item))
    return linked


def sync_requisitioners_to_directory(requisitioners, *, document=None):
    """Backward-compatible alias used by document upload/edit views."""
    return link_document_requisitioners(requisitioners, document=document)


def _refresh_requestor_for_documents(document_ids):
    from documents.models import Document

    if not document_ids:
        return

    documents = Document.objects.filter(id__in=document_ids).prefetch_related("requisitioners")
    from documents.requisitioners import format_requisitioners_display

    for document in documents:
        display_value = format_requisitioners_display(document.requisitioners.all()) or None
        if document.requestor != display_value:
            document.requestor = display_value
            document.save(update_fields=["requestor", "updated_at"])


def _upsert_by_employee_number(*, employee_number, first_name, last_name, suffix, employee_instance=None):
    if employee_instance is not None:
        employee = employee_instance
        employee.employee_number = employee_number
        employee.first_name = first_name
        employee.last_name = last_name
        employee.suffix = suffix
        employee.is_active = True
        employee.save(
            update_fields=["employee_number", "first_name", "last_name", "suffix", "is_active", "updated_at"]
        )
    else:
        employee, _created = Employee.objects.update_or_create(
            employee_number=employee_number,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "suffix": suffix,
                "is_active": True,
            },
        )

    requisitioners = DocumentRequisitioner.objects.filter(
        Q(employee_id=employee.id) | Q(employee_number__iexact=employee_number)
    )
    affected_document_ids = set(requisitioners.values_list("document_id", flat=True))
    requisitioners.update(
        employee_id=employee.id,
        source=DocumentRequisitioner.SOURCE_DIRECTORY,
        employee_number=employee_number,
        first_name=first_name,
        last_name=last_name,
        suffix=suffix,
    )
    _refresh_requestor_for_documents(affected_document_ids)
    return employee


def _find_name_only_employee(first_name, last_name, suffix=""):
    return (
        Employee.objects.filter(
            employee_number__isnull=True,
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            suffix=suffix or "",
        )
        .order_by("id")
        .first()
    )


def _upsert_by_name(*, first_name, last_name, suffix, employee_instance=None):
    if employee_instance is not None:
        employee = employee_instance
        employee.first_name = first_name
        employee.last_name = last_name
        employee.suffix = suffix
        employee.is_active = True
        employee.save(update_fields=["first_name", "last_name", "suffix", "is_active", "updated_at"])
    else:
        employee = _find_name_only_employee(first_name, last_name, suffix)
        if employee:
            employee.first_name = first_name
            employee.last_name = last_name
            employee.suffix = suffix
            employee.is_active = True
            employee.save(update_fields=["first_name", "last_name", "suffix", "is_active", "updated_at"])
        else:
            employee = Employee.objects.create(
                employee_number=None,
                first_name=first_name,
                last_name=last_name,
                suffix=suffix,
                is_active=True,
            )

    requisitioners = DocumentRequisitioner.objects.filter(
        Q(employee_id=employee.id)
        | Q(
            employee_id__isnull=True,
            employee_number__isnull=True,
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            suffix=suffix or "",
        )
    )
    affected_document_ids = set(requisitioners.values_list("document_id", flat=True))
    requisitioners.update(
        employee_id=employee.id,
        source=DocumentRequisitioner.SOURCE_DIRECTORY,
        first_name=first_name,
        last_name=last_name,
        suffix=suffix,
    )
    _refresh_requestor_for_documents(affected_document_ids)
    return employee


def upsert_employee_and_cascade(
    *,
    first_name,
    last_name,
    suffix="",
    employee_number=None,
    document=None,
    employee_instance=None,
):
    """Admin directory upsert — updates master Employee and linked document tag snapshots."""
    del document

    normalized_first = normalize_name_part(first_name)
    normalized_last = normalize_name_part(last_name)
    normalized_suffix = (suffix or "").strip()
    cleaned_number = normalize_employee_number(employee_number or "") or None

    if cleaned_number:
        return _upsert_by_employee_number(
            employee_number=cleaned_number,
            first_name=normalized_first,
            last_name=normalized_last,
            suffix=normalized_suffix,
            employee_instance=employee_instance,
        )

    return _upsert_by_name(
        first_name=normalized_first,
        last_name=normalized_last,
        suffix=normalized_suffix,
        employee_instance=employee_instance,
    )
