from django.db.models import Q

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auditlogs.models import log_audit
from config.pagination import StandardResultsSetPagination
from documents.permissions import get_accessible_org_unit_ids

from .models import Employee
from .permissions import (
    assert_directory_admin,
    assert_directory_read,
    log_directory_access_denied,
)
from .references import (
    annotate_employee_reference_counts,
    get_delete_api_message,
    get_reference_count_for_employee,
    get_tagged_documents_queryset,
)
from .validation import build_employee_number_audit_details, employee_number_changed
from .serializers import (
    EmployeeSearchSerializer,
    EmployeeSerializer,
    EmployeeUpsertSerializer,
    RequisitionerTaggedDocumentSerializer,
)


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "list" and not self._is_directory_reader():
            return EmployeeSearchSerializer
        return EmployeeSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def _is_directory_admin(self):
        return getattr(self.request.user, "role", None) == "admin"

    def _is_directory_reader(self):
        return getattr(self.request.user, "role", None) in {"admin", "dept_head"}

    def _list_search_query(self):
        return (self.request.query_params.get("search") or "").strip()

    def _scope_org_unit_ids(self):
        if self._is_directory_admin():
            return None
        return get_accessible_org_unit_ids(self.request.user)

    def get_queryset(self):
        queryset = Employee.objects.all()

        if self.action == "list":
            search = self._list_search_query()
            active_only = self.request.query_params.get("activeOnly", "true").lower() != "false"

            if active_only:
                queryset = queryset.filter(is_active=True)

            if search:
                queryset = queryset.filter(
                    Q(employee_number__icontains=search)
                    | Q(first_name__icontains=search)
                    | Q(last_name__icontains=search)
                    | Q(suffix__icontains=search)
                )

        if self._is_directory_reader():
            return annotate_employee_reference_counts(
                queryset,
                scope_org_unit_ids=self._scope_org_unit_ids(),
            ).order_by("last_name", "first_name")

        return queryset.order_by("last_name", "first_name")

    def _assert_admin(self):
        assert_directory_admin(self.request.user)

    def _assert_directory_reader(self):
        if self._is_directory_reader():
            return
        log_directory_access_denied(
            self.request.user,
            self.request,
            "Requisitioners Directory record",
        )
        raise PermissionDenied("You do not have permission to access the Requisitioners Directory.")

    def _audit_directory_list(self):
        user = self.request.user
        org_name = user.org_unit.name if getattr(user, "org_unit", None) else "Global Access"
        log_audit(
            user,
            "VIEW_REQUISITIONERS_DIRECTORY",
            f"Viewed Requisitioners Directory ({user.email}, {user.role}, {org_name})",
            target_type="Employee",
            target_name="Requisitioners Directory",
            target_org_unit=org_name if getattr(user, "org_unit", None) else None,
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )

    def list(self, request, *args, **kwargs):
        assert_directory_read(request.user, search=self._list_search_query(), request=request)
        response = super().list(request, *args, **kwargs)
        if self._is_directory_reader():
            self._audit_directory_list()
        return response

    def retrieve(self, request, *args, **kwargs):
        self._assert_directory_reader()
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=["post"], url_path="check-duplicate")
    def check_duplicate(self, request):
        from .duplicate_detection import check_manual_requisitioner_duplicates

        duplicate = check_manual_requisitioner_duplicates(
            employee_number=request.data.get("employeeNumber") or request.data.get("employee_number"),
            first_name=request.data.get("firstName") or request.data.get("first_name") or "",
            last_name=request.data.get("lastName") or request.data.get("last_name") or "",
            suffix=request.data.get("suffix") or "",
            exclude_employee_id=request.data.get("excludeEmployeeId") or request.data.get("employeeId"),
        )
        return Response(
            {
                "blocked": duplicate["blocked"],
                "message": duplicate["message"],
                "matches": duplicate["matches"],
            }
        )

    @action(detail=False, methods=["post"], url_path="upsert")
    def upsert(self, request):
        self._assert_admin()
        serializer = EmployeeUpsertSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        log_audit(
            request.user,
            "UPSERT_REQUISITIONER_DIRECTORY",
            f"Upserted Requisitioners Directory record: {employee.get_full_name()} ({employee.employee_number})",
            target_type="Employee",
            target_name=employee.get_full_name(),
        )
        return Response(
            EmployeeSerializer(employee, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="documents")
    def documents(self, request, pk=None):
        self._assert_directory_reader()
        employee = self.get_object()
        name = employee.get_full_name()
        number = employee.employee_number or "No Emp No. Provided"
        scope_ids = self._scope_org_unit_ids()

        log_audit(
            request.user,
            "VIEW_REQUISITIONER_DOCUMENT_REFERENCES",
            f"Viewed document references for {name} ({number})",
            target_type="Employee",
            target_name=name,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        queryset = get_tagged_documents_queryset(employee, scope_org_unit_ids=scope_ids).select_related(
            "folder", "folder__org_unit", "category", "uploader"
        )

        search = (request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(code__icontains=search)
            )

        category = (request.query_params.get("category") or "").strip()
        if category:
            queryset = queryset.filter(category__name__icontains=category)

        org_unit = (request.query_params.get("orgUnit") or "").strip()
        if org_unit:
            queryset = queryset.filter(folder__org_unit__name__icontains=org_unit)

        total_tagged = get_reference_count_for_employee(employee, scope_org_unit_ids=scope_ids)

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = RequisitionerTaggedDocumentSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data["totalTaggedDocuments"] = total_tagged
        return response

    def create(self, request, *args, **kwargs):
        self._assert_admin()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        log_audit(
            request.user,
            "CREATE_EMPLOYEE",
            f"Created Requisitioners Directory record: {employee.get_full_name()} ({employee.employee_number})",
            target_type="Employee",
            target_name=employee.get_full_name(),
        )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        self._assert_admin()
        employee = self.get_object()
        old_number = employee.employee_number
        tagged_count_before = get_reference_count_for_employee(employee)
        override_reason = (request.data.get("employeeNumberOverrideReason") or "").strip()

        response = super().update(request, *args, **kwargs)

        employee.refresh_from_db()
        new_number = employee.employee_number
        number_changed = employee_number_changed(old_number, new_number)

        if number_changed:
            action = (
                "UPDATE_EMPLOYEE_NUMBER_OVERRIDE"
                if tagged_count_before > 0
                else "UPDATE_EMPLOYEE_NUMBER"
            )
            log_audit(
                request.user,
                action,
                build_employee_number_audit_details(
                    employee_id=employee.id,
                    old_number=old_number,
                    new_number=new_number,
                    user_email=request.user.email,
                    override_reason=override_reason if tagged_count_before > 0 else None,
                ),
                target_type="Employee",
                target_name=employee.get_full_name(),
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        else:
            log_audit(
                request.user,
                "UPDATE_EMPLOYEE",
                f"Updated Requisitioners Directory record: {employee.get_full_name()} ({employee.employee_number or 'No Emp No. Provided'})",
                target_type="Employee",
                target_name=employee.get_full_name(),
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        return response

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._assert_admin()
        employee = self.get_object()
        name = employee.get_full_name()
        number = employee.employee_number or "No Emp No. Provided"
        reference_count = get_reference_count_for_employee(employee)

        if reference_count > 3:
            log_audit(
                request.user,
                "REQUISITIONER_DELETE_BLOCKED",
                (
                    f"Blocked delete for Requisitioners Directory record: {name} ({number}). "
                    f"Tagged on {reference_count} documents."
                ),
                target_type="Employee",
                target_name=name,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            return Response(
                {
                    "success": False,
                    "message": get_delete_api_message(reference_count),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = super().destroy(request, *args, **kwargs)
        log_audit(
            request.user,
            "DELETE_EMPLOYEE",
            (
                f"Deleted Requisitioners Directory record: {name} ({number}). "
                f"Tagged on {reference_count} documents."
            ),
            target_type="Employee",
            target_name=name,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return response
