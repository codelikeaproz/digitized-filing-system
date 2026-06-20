from django.db.models import Case, Count, IntegerField, OuterRef, Q, Subquery, When
from django.db.models.functions import Coalesce

from documents.models import DocumentRequisitioner

MAX_DELETE_REFERENCES = 3

ACTIVE_DOCUMENT_FILTERS = Q(
    document__is_deleted=False,
    document__folder__is_deleted=False,
    document__folder__org_unit__is_deleted=False,
)


def _apply_scope(filters, scope_org_unit_ids):
    if scope_org_unit_ids is not None:
        filters &= Q(document__folder__org_unit_id__in=scope_org_unit_ids)
    return filters


def _employee_id_filter(employee_id, *, scope_org_unit_ids=None):
    return _apply_scope(
        Q(employee_id=employee_id) & ACTIVE_DOCUMENT_FILTERS,
        scope_org_unit_ids,
    )


def get_reference_count_by_employee_id(employee_id, *, scope_org_unit_ids=None):
    return (
        DocumentRequisitioner.objects.filter(_employee_id_filter(employee_id, scope_org_unit_ids=scope_org_unit_ids))
        .values("document_id")
        .distinct()
        .count()
    )


def get_reference_count_by_name(first_name, last_name, suffix="", *, scope_org_unit_ids=None):
    filters = _apply_scope(
        Q(
            employee_id__isnull=True,
            employee_number__isnull=True,
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            suffix=suffix or "",
        )
        & ACTIVE_DOCUMENT_FILTERS,
        scope_org_unit_ids,
    )

    return (
        DocumentRequisitioner.objects.filter(filters)
        .values("document_id")
        .distinct()
        .count()
    )


def get_reference_count(employee_number, *, scope_org_unit_ids=None):
    if not employee_number:
        return 0

    filters = _apply_scope(
        Q(employee_id__isnull=True, employee_number__iexact=employee_number) & ACTIVE_DOCUMENT_FILTERS,
        scope_org_unit_ids,
    )

    return (
        DocumentRequisitioner.objects.filter(filters)
        .values("document_id")
        .distinct()
        .count()
    )


def get_reference_count_for_employee(employee, *, scope_org_unit_ids=None):
    fk_count = get_reference_count_by_employee_id(employee.id, scope_org_unit_ids=scope_org_unit_ids)
    if fk_count:
        return fk_count

    if employee.employee_number:
        legacy = get_reference_count(employee.employee_number, scope_org_unit_ids=scope_org_unit_ids)
        if legacy:
            return legacy

    return get_reference_count_by_name(
        employee.first_name,
        employee.last_name,
        employee.suffix,
        scope_org_unit_ids=scope_org_unit_ids,
    )


def get_tagged_documents_queryset(employee, *, scope_org_unit_ids=None):
    from documents.models import Document

    queryset = Document.objects.filter(
        is_deleted=False,
        folder__is_deleted=False,
        folder__org_unit__is_deleted=False,
    )

    fk_matches = queryset.filter(requisitioners__employee_id=employee.id).distinct()
    if fk_matches.exists():
        queryset = fk_matches
    elif employee.employee_number:
        queryset = queryset.filter(
            requisitioners__employee_id__isnull=True,
            requisitioners__employee_number__iexact=employee.employee_number,
        ).distinct()
    else:
        queryset = queryset.filter(
            requisitioners__employee_id__isnull=True,
            requisitioners__employee_number__isnull=True,
            requisitioners__first_name__iexact=employee.first_name,
            requisitioners__last_name__iexact=employee.last_name,
            requisitioners__suffix=employee.suffix or "",
        ).distinct()

    if scope_org_unit_ids is not None:
        queryset = queryset.filter(folder__org_unit_id__in=scope_org_unit_ids)
    return queryset.order_by("-created_at")


def can_delete_requisitioner(count):
    return count <= MAX_DELETE_REFERENCES


def get_delete_block_reason(count):
    if can_delete_requisitioner(count):
        return ""
    return "Cannot delete. Tagged on more than 3 documents."


def get_delete_block_message(count):
    if can_delete_requisitioner(count):
        return ""
    document_label = "document" if count == 1 else "documents"
    return (
        f"Cannot delete requisitioner. "
        f"This requisitioner is currently tagged on {count} {document_label}. "
        f"Remove or update document tags before deletion."
    )


def get_delete_api_message(count):
    document_label = "document" if count == 1 else "documents"
    return f"Cannot delete requisitioner. Tagged on {count} {document_label}."


def annotate_employee_reference_counts(queryset, *, scope_org_unit_ids=None):
    employee_id_filter = _apply_scope(
        Q(employee_id=OuterRef("pk")) & ACTIVE_DOCUMENT_FILTERS,
        scope_org_unit_ids,
    )
    employee_id_subquery = (
        DocumentRequisitioner.objects.filter(employee_id_filter)
        .values("employee_id")
        .annotate(cnt=Count("document_id", distinct=True))
        .values("cnt")[:1]
    )

    number_filter = _apply_scope(
        Q(
            employee_id__isnull=True,
            employee_number__iexact=OuterRef("employee_number"),
        )
        & ACTIVE_DOCUMENT_FILTERS,
        scope_org_unit_ids,
    )
    number_subquery = (
        DocumentRequisitioner.objects.filter(number_filter)
        .values("employee_number")
        .annotate(cnt=Count("document_id", distinct=True))
        .values("cnt")[:1]
    )

    name_filter = _apply_scope(
        Q(
            employee_id__isnull=True,
            employee_number__isnull=True,
            first_name__iexact=OuterRef("first_name"),
            last_name__iexact=OuterRef("last_name"),
            suffix=OuterRef("suffix"),
        )
        & ACTIVE_DOCUMENT_FILTERS,
        scope_org_unit_ids,
    )
    name_subquery = (
        DocumentRequisitioner.objects.filter(name_filter)
        .values("first_name")
        .annotate(cnt=Count("document_id", distinct=True))
        .values("cnt")[:1]
    )

    queryset = queryset.annotate(
        referenced_document_count=Coalesce(
            Subquery(employee_id_subquery),
            Case(
                When(employee_number__isnull=False, then=Subquery(number_subquery)),
                default=Subquery(name_subquery),
                output_field=IntegerField(),
            ),
            0,
        )
    )

    if scope_org_unit_ids is not None:
        scoped_employee_id_filter = employee_id_filter & Q(
            document__folder__org_unit_id__in=scope_org_unit_ids
        )
        scoped_employee_id_subquery = (
            DocumentRequisitioner.objects.filter(scoped_employee_id_filter)
            .values("employee_id")
            .annotate(cnt=Count("document_id", distinct=True))
            .values("cnt")[:1]
        )
        scoped_number_filter = number_filter & Q(document__folder__org_unit_id__in=scope_org_unit_ids)
        scoped_number_subquery = (
            DocumentRequisitioner.objects.filter(scoped_number_filter)
            .values("employee_number")
            .annotate(cnt=Count("document_id", distinct=True))
            .values("cnt")[:1]
        )
        scoped_name_filter = name_filter & Q(document__folder__org_unit_id__in=scope_org_unit_ids)
        scoped_name_subquery = (
            DocumentRequisitioner.objects.filter(scoped_name_filter)
            .values("first_name")
            .annotate(cnt=Count("document_id", distinct=True))
            .values("cnt")[:1]
        )
        queryset = queryset.annotate(
            scoped_referenced_document_count=Coalesce(
                Subquery(scoped_employee_id_subquery),
                Case(
                    When(employee_number__isnull=False, then=Subquery(scoped_number_subquery)),
                    default=Subquery(scoped_name_subquery),
                    output_field=IntegerField(),
                ),
                0,
            )
        )

    return queryset
