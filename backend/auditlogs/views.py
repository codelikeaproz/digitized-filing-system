import csv
from datetime import datetime, time

from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework import viewsets

from config.pagination import StandardResultsSetPagination
from config.timezone_utils import format_local_datetime
from orgunits.models import OrgUnit
from .models import AuditLog, log_audit
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ModelViewSet):
    serializer_class = AuditLogSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = AuditLog.objects.select_related("user", "user__org_unit").order_by("-created_at")
        return self._apply_filters(queryset)

    def _scope_queryset(self, queryset):
        user = self.request.user
        role = getattr(user, "role", None)
        if role == "admin":
            return queryset
        if role == "dept_head":
            org_unit = getattr(user, "org_unit", None)
            if not org_unit:
                return queryset.none()
            scoped_org_units = [org_unit, *org_unit.get_all_children()]
            scoped_ids = [unit.id for unit in scoped_org_units]
            scoped_names = [unit.name for unit in scoped_org_units]
            return queryset.filter(Q(user__org_unit_id__in=scoped_ids) | Q(target_org_unit__in=scoped_names))
        raise PermissionDenied("You do not have access to audit logs.")

    def _parse_date_boundary(self, value, *, end_of_day=False):
        parsed_date = parse_date(value or "")
        if not parsed_date:
            raise ValidationError({"date_range": "Date must use YYYY-MM-DD format."})
        boundary_time = time.max if end_of_day else time.min
        parsed_datetime = datetime.combine(parsed_date, boundary_time)
        return timezone.make_aware(parsed_datetime, timezone.get_current_timezone())

    def _apply_filters(self, queryset):
        queryset = self._scope_queryset(queryset)
        search = self.request.query_params.get("search")
        action = self.request.query_params.get("action")
        role = self.request.query_params.get("role")
        org_unit = self.request.query_params.get("orgUnit") or self.request.query_params.get("org_unit")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if search:
            queryset = queryset.filter(
                Q(action__icontains=search)
                | Q(details__icontains=search)
                | Q(user_email__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
            )
        if action:
            queryset = queryset.filter(action=action)
        if role:
            queryset = queryset.filter(user__role__iexact=role)
        if org_unit:
            if org_unit == "Global Access":
                queryset = queryset.filter(Q(target_org_unit__isnull=True) | Q(target_org_unit=""), user__org_unit__isnull=True)
            elif str(org_unit).isdigit():
                target_org_unit = OrgUnit.objects.filter(pk=org_unit).first()
                if target_org_unit:
                    queryset = queryset.filter(Q(target_org_unit=target_org_unit.name) | Q(user__org_unit_id=target_org_unit.id))
                else:
                    queryset = queryset.none()
            else:
                queryset = queryset.filter(Q(target_org_unit=org_unit) | Q(user__org_unit__name=org_unit))
        if start_date:
            queryset = queryset.filter(created_at__gte=self._parse_date_boundary(start_date))
        if end_date:
            queryset = queryset.filter(created_at__lte=self._parse_date_boundary(end_date, end_of_day=True))
        return queryset

    def _export_filter_details(self):
        query_params = self.request.query_params
        filters = []
        filter_keys = [
            ("search", "search"),
            ("action", "action"),
            ("role", "role"),
            ("org_unit", "org_unit"),
            ("orgUnit", "org_unit"),
            ("start_date", "start_date"),
            ("end_date", "end_date"),
        ]
        for source_key, display_key in filter_keys:
            value = query_params.get(source_key)
            if value:
                filters.append(f"{display_key}={value}")
        return ", ".join(filters)

    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        queryset = self._apply_filters(
            AuditLog.objects.select_related("user", "user__org_unit").order_by("-created_at")
        )
        rows = list(queryset)
        filter_details = self._export_filter_details()

        audit_details = "Exported audit logs CSV"
        if filter_details:
            audit_details = f"{audit_details} with filters: {filter_details}"
        log_audit(
            request.user,
            "EXPORT_AUDIT_CSV",
            audit_details,
            target_type="AuditLog",
            target_name="audit_logs.csv",
            target_org_unit=request.user.org_unit.name if getattr(request.user, "org_unit", None) else None,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        today = timezone.localdate().isoformat()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="audit_logs_{today}.csv"'

        writer = csv.writer(response)
        writer.writerow(["Timestamp", "Name", "Role", "Org Unit", "Action", "Details"])

        for log in rows:
            user = log.user
            name = user.get_full_name() or user.email if user else "System"
            role = getattr(user, "role", None) or "System"
            org_unit = log.target_org_unit or (user.org_unit.name if user and user.org_unit else "Global Access")
            # Excel may render date/time cells as ####### when the column is narrow.
            # Wrapping the formatted timestamp in ="..." keeps it readable as text.
            timestamp = f'="{format_local_datetime(log.created_at)}"'
            writer.writerow([timestamp, name, role, org_unit, log.action, log.details])

        return response

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(
            user=user,
            user_email=getattr(user, "email", "") or "system",
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )
