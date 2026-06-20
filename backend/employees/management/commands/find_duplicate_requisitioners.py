"""Report duplicate or split Requisitioners Directory rows for manual cleanup."""
from collections import defaultdict

from django.core.management.base import BaseCommand

from documents.requisitioners import normalize_name_part
from employees.models import Employee


class Command(BaseCommand):
    help = (
        "Report duplicate Requisitioners Directory rows (same number, same name, "
        "or number + name-only pairs). Use output to plan manual merge/cleanup."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            help="Include inactive Employee rows in the report.",
        )

    def handle(self, *args, **options):
        include_inactive = options.get("include_inactive")
        queryset = Employee.objects.all()
        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        employees = list(queryset.order_by("last_name", "first_name", "id"))
        if not employees:
            self.stdout.write(self.style.WARNING("No requisitioner directory rows found."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Duplicate employee numbers (case variants)"))
        self._report_number_groups(employees)

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Duplicate normalized names (multiple directory rows)"))
        self._report_name_groups(employees)

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING("Number + name-only pairs (same person, split rows)")
        )
        self._report_number_name_only_pairs(employees)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Cleanup guidance:"))
        self.stdout.write(
            "1. Pick the canonical Employee row (prefer rows with an employee number and FK-linked tags)."
        )
        self.stdout.write(
            "2. Update DocumentRequisitioner rows to point at the canonical employee_id "
            "(source=directory) and refresh snapshots from the master record."
        )
        self.stdout.write(
            "3. Deactivate or delete orphan Employee rows after references are consolidated."
        )
        self.stdout.write(
            "4. Re-run this command until no duplicate groups remain."
        )

    def _format_employee(self, employee):
        number = employee.employee_number or "No Emp No. Provided"
        return f"#{employee.id} {number} — {employee.get_full_name()}"

    def _report_number_groups(self, employees):
        groups = defaultdict(list)
        for employee in employees:
            if not employee.employee_number:
                continue
            groups[employee.employee_number.strip().upper()].append(employee)

        found = False
        for normalized_number, group in sorted(groups.items()):
            if len(group) < 2:
                continue
            found = True
            self.stdout.write(f"  {normalized_number}:")
            for employee in group:
                self.stdout.write(f"    - {self._format_employee(employee)}")

        if not found:
            self.stdout.write("  None found.")

    def _report_name_groups(self, employees):
        groups = defaultdict(list)
        for employee in employees:
            key = (
                normalize_name_part(employee.first_name).lower(),
                normalize_name_part(employee.last_name).lower(),
                (employee.suffix or "").strip(),
            )
            groups[key].append(employee)

        found = False
        for key, group in sorted(groups.items(), key=lambda item: (item[0][1], item[0][0])):
            if len(group) < 2:
                continue
            found = True
            label = " ".join(part for part in [group[0].first_name, group[0].last_name, group[0].suffix or ""] if part)
            self.stdout.write(f"  {label} ({len(group)} rows):")
            for employee in group:
                self.stdout.write(f"    - {self._format_employee(employee)}")

        if not found:
            self.stdout.write("  None found.")

    def _report_number_name_only_pairs(self, employees):
        by_name = defaultdict(list)
        for employee in employees:
            key = (
                normalize_name_part(employee.first_name).lower(),
                normalize_name_part(employee.last_name).lower(),
                (employee.suffix or "").strip(),
            )
            by_name[key].append(employee)

        found = False
        for group in by_name.values():
            with_number = [employee for employee in group if employee.employee_number]
            without_number = [employee for employee in group if not employee.employee_number]
            if not with_number or not without_number:
                continue
            found = True
            label = group[0].get_full_name()
            self.stdout.write(f"  {label}:")
            for employee in with_number + without_number:
                self.stdout.write(f"    - {self._format_employee(employee)}")

        if not found:
            self.stdout.write("  None found.")
