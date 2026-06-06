"""
Audit log API — read, export, and optional client-side event creation.

Scope:
    Admin — all logs
    Dept Head — logs for users/targets in own OrgUnit subtree
    Staff — denied

Exports:
    GET .../export-xlsx/
"""
import io
import zipfile
from datetime import datetime, time
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.db.models import CharField, Count, F, Q, Value
from django.db.models.functions import Coalesce, NullIf
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
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

    def _audit_export_rows(self, rows):
        export_rows = []
        for log in rows:
            user = log.user
            name = user.get_full_name() or user.email if user else "System"
            role = getattr(user, "role", None) or "System"
            org_unit = log.target_org_unit or (user.org_unit.name if user and user.org_unit else "Global Access")
            export_rows.append(
                [
                    format_local_datetime(log.created_at),
                    name,
                    role.replace("_", " ").upper(),
                    org_unit.upper(),
                    log.action.upper(),
                    log.details,
                ]
            )
        return export_rows

    def _build_audit_xlsx(self, rows):
        headers = ["TIMESTAMP", "NAME", "ROLE", "ORG UNIT", "ACTION", "DETAILS"]
        data_rows = [headers, *self._audit_export_rows(rows)]
        column_widths = [24, 24, 18, 24, 28, 72]

        def cell_ref(row_index, column_index):
            column_name = ""
            index = column_index
            while index:
                index, remainder = divmod(index - 1, 26)
                column_name = chr(65 + remainder) + column_name
            return f"{column_name}{row_index}"

        def cell_xml(value, row_index, column_index, style_id):
            text = escape(str(value or ""))
            return (
                f'<c r="{cell_ref(row_index, column_index)}" t="inlineStr" s="{style_id}">'
                f"<is><t>{text}</t></is></c>"
            )

        sheet_rows = []
        for row_index, row in enumerate(data_rows, start=1):
            style_id = 1 if row_index == 1 else 2
            cells = "".join(
                cell_xml(value, row_index, column_index, style_id)
                for column_index, value in enumerate(row, start=1)
            )
            row_height = ' ht="24" customHeight="1"' if row_index == 1 else ""
            sheet_rows.append(f'<row r="{row_index}"{row_height}>{cells}</row>')

        cols = "".join(
            f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
            for index, width in enumerate(column_widths, start=1)
        )
        last_row = max(len(data_rows), 1)
        sheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <dimension ref="A1:F{last_row}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <cols>{cols}</cols>
  <sheetData>{''.join(sheet_rows)}</sheetData>
  <autoFilter ref="A1:F{last_row}"/>
</worksheet>'''
        styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="3">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
    <font><sz val="11"/><name val="Calibri"/></font>
  </fonts>
  <fills count="3">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF0A4D27"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border><left style="thin"><color rgb="FFD7E5D8"/></left><right style="thin"><color rgb="FFD7E5D8"/></right><top style="thin"><color rgb="FFD7E5D8"/></top><bottom style="thin"><color rgb="FFD7E5D8"/></bottom><diagonal/></border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="3">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="2" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''
        workbook_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="AUDIT LOGS" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''
        workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
        root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
        content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''

        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", content_types)
            archive.writestr("_rels/.rels", root_rels)
            archive.writestr("xl/workbook.xml", workbook_xml)
            archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            archive.writestr("xl/styles.xml", styles_xml)
            archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        return output.getvalue()

    @action(detail=False, methods=["get"], url_path="analytics")
    def analytics(self, request):
        """
        Aggregate audit activity per Office Unit for dashboard charts.
        Returns upload, delete, and edit counts grouped by target_org_unit.
        """
        queryset = self._apply_filters(
            AuditLog.objects.select_related("user", "user__org_unit").order_by("-created_at")
        )

        upload_actions = ["UPLOAD", "SCAN_UPLOAD"]
        delete_actions = ["DELETE_FOLDER", "PERMANENT_DELETE_FOLDER", "PERMANENT_DELETE_DOCUMENT"]
        edit_actions = ["EDIT_DOCUMENT"]

        def aggregate_by_org_unit(action_list):
            # Prefer target_org_unit (e.g. folder Office Unit on upload/edit).
            # Fall back to the acting user's Office Unit for older log rows.
            rows = (
                queryset.filter(action__in=action_list)
                .annotate(
                    org_unit_name=Coalesce(
                        NullIf(F("target_org_unit"), Value("")),
                        F("user__org_unit__name"),
                        output_field=CharField(),
                    )
                )
                .exclude(org_unit_name__isnull=True)
                .values("org_unit_name")
                .annotate(count=Count("id"))
                .order_by("-count", "org_unit_name")
            )
            return [
                {"org_unit": row["org_unit_name"], "count": row["count"]}
                for row in rows
            ]

        return Response(
            {
                "uploads_by_org_unit": aggregate_by_org_unit(upload_actions),
                "deletes_by_org_unit": aggregate_by_org_unit(delete_actions),
                "edits_by_org_unit": aggregate_by_org_unit(edit_actions),
            }
        )

    @action(detail=False, methods=["get"], url_path="export-xlsx")
    def export_xlsx(self, request):
        queryset = self._apply_filters(
            AuditLog.objects.select_related("user", "user__org_unit").order_by("-created_at")
        )
        rows = list(queryset)
        filter_details = self._export_filter_details()

        audit_details = "Exported audit logs Excel"
        if filter_details:
            audit_details = f"{audit_details} with filters: {filter_details}"
        log_audit(
            request.user,
            "EXPORT_AUDIT_XLSX",
            audit_details,
            target_type="AuditLog",
            target_name="audit_logs.xlsx",
            target_org_unit=request.user.org_unit.name if getattr(request.user, "org_unit", None) else None,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        today = timezone.localdate().isoformat()
        response = HttpResponse(
            self._build_audit_xlsx(rows),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="audit_logs_{today}.xlsx"'
        return response

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(
            user=user,
            user_email=getattr(user, "email", "") or "system",
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )
