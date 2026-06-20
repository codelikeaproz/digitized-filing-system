"""
Requisitioners Directory intents for the Document Assistant.

Uses the same tagged-document identity rules as the Requisitioners Directory
(employees.references) rather than partial document-search matching.
"""
import re

from django.db.models import Q

from config.employee_number import normalize_employee_number
from documents.permissions import get_accessible_org_unit_ids
from employees.models import Employee
from employees.references import (
    annotate_employee_reference_counts,
    get_reference_count_for_employee,
    get_tagged_documents_queryset,
)

from .chatbot_limits import chatbot_list_limit
from .intent_service import (
    clean_name,
    document_matches,
    format_document_line,
    list_more_note,
    list_response_metadata,
    normalize_query,
    pluralize_document,
)


DIRECTORY_MARKERS = (
    "tagged on",
    "tagged to",
    "tagged documents",
    "requisitioners directory",
    "in the directory",
    "find requisitioner",
    "which requisitioners have",
    "list requisitioners with tagged",
    "who has the most tagged",
    "most tagged documents",
)

TAGGED_COUNT_PATTERNS = [
    re.compile(r"\bhow many documents (?:is|are) (.+?) tagged on\b", re.IGNORECASE),
    re.compile(
        r"\bhow many (?:documents|files) (?:is|are) tagged (?:to|on) (.+?)(?:[?.!]|$)",
        re.IGNORECASE,
    ),
    re.compile(r"\bhow many tagged documents (?:does|do) (.+?) have\b", re.IGNORECASE),
]

LIST_TAGGED_PATTERNS = [
    re.compile(r"\b(?:list|show) documents tagged (?:to|on) (.+?)(?:[?.!]|$)", re.IGNORECASE),
    re.compile(r"\b(?:list|show) tagged documents (?:for|of|to) (.+?)(?:[?.!]|$)", re.IGNORECASE),
]

FIND_REQUISITIONER_PATTERNS = [
    re.compile(r"\bfind requisitioner (?:by employee number )?(.+?)(?:[?.!]|$)", re.IGNORECASE),
    re.compile(r"\bfind requisitioner named (.+?)(?:[?.!]|$)", re.IGNORECASE),
]

CATALOG_TAGGED_PATTERNS = [
    re.compile(r"\bwhich requisitioners have tagged documents\b", re.IGNORECASE),
    re.compile(r"\blist requisitioners with tagged documents\b", re.IGNORECASE),
]

MOST_TAGGED_PATTERNS = [
    re.compile(r"\bwho has the most tagged documents\b", re.IGNORECASE),
    re.compile(r"\bwhich requisitioner has the most tagged documents\b", re.IGNORECASE),
    re.compile(r"\brequisitioner with the most tagged documents\b", re.IGNORECASE),
]


def is_requisitioner_directory_query(query):
    normalized = normalize_query(query).lower()
    return any(marker in normalized for marker in DIRECTORY_MARKERS)


def scope_org_unit_ids_for_user(user):
    if getattr(user, "role", None) == "admin":
        return None
    return get_accessible_org_unit_ids(user)


def format_employee_number_display(employee_number):
    return employee_number or "No Emp No. Provided"


def format_employee_summary(employee, count):
    return (
        f"- {employee.get_full_name()} ({format_employee_number_display(employee.employee_number)}): "
        f"{count} tagged {pluralize_document(count)}"
    )


def tagged_count_for_user(user, employee):
    return get_reference_count_for_employee(
        employee,
        scope_org_unit_ids=scope_org_unit_ids_for_user(user),
    )


def find_directory_employees(search_text, limit=None):
    if limit is None:
        limit = chatbot_list_limit()

    cleaned = clean_name(search_text)
    if not cleaned:
        return []

    queryset = Employee.objects.filter(is_active=True)
    normalized_number = normalize_employee_number(cleaned)
    if normalized_number:
        exact = list(queryset.filter(employee_number__iexact=normalized_number)[:limit])
        if exact:
            return exact
        partial_number = list(queryset.filter(employee_number__icontains=normalized_number)[:limit])
        if partial_number:
            return partial_number

    parts = cleaned.split()
    if len(parts) == 1:
        token = parts[0]
        return list(
            queryset.filter(
                Q(first_name__icontains=token)
                | Q(last_name__icontains=token)
                | Q(employee_number__icontains=token)
            ).order_by("last_name", "first_name")[:limit]
        )

    first_name = parts[0]
    last_name = parts[-1]
    exact_name = list(
        queryset.filter(
            Q(first_name__icontains=first_name) & Q(last_name__icontains=last_name)
        ).order_by("last_name", "first_name")[:limit]
    )
    if exact_name:
        return exact_name

    combined = list(
        queryset.filter(
            Q(first_name__icontains=cleaned)
            | Q(last_name__icontains=cleaned)
            | Q(first_name__icontains=first_name)
            | Q(last_name__icontains=last_name)
        ).order_by("last_name", "first_name")[:limit]
    )
    return combined


def extract_directory_search_text(query, patterns):
    normalized = normalize_query(query)
    for pattern in patterns:
        match = pattern.search(normalized)
        if match:
            value = clean_name(match.group(1))
            if value:
                return value
    return ""


def resolve_single_employee(user, search_text):
    employees = find_directory_employees(search_text, limit=chatbot_list_limit())
    if not employees:
        return None, []

    if len(employees) == 1:
        return employees[0], employees

    scoped_counts = [tagged_count_for_user(user, employee) for employee in employees]
    with_tags = [employee for employee, count in zip(employees, scoped_counts) if count > 0]
    if len(with_tags) == 1:
        return with_tags[0], employees

    normalized_number = normalize_employee_number(search_text)
    if normalized_number:
        exact_number = [
            employee
            for employee in employees
            if employee.employee_number
            and employee.employee_number.upper() == normalized_number
        ]
        if len(exact_number) == 1:
            return exact_number[0], employees

    return None, employees


def tagged_documents_for_user(user, employee):
    scope_ids = scope_org_unit_ids_for_user(user)
    if scope_ids is not None and not scope_ids:
        return get_tagged_documents_queryset(employee, scope_org_unit_ids=[]).none()
    return get_tagged_documents_queryset(employee, scope_org_unit_ids=scope_ids)


def multiple_matches_answer(user, employees, search_text):
    lines = "\n".join(
        format_employee_summary(employee, tagged_count_for_user(user, employee))
        for employee in employees
    )
    return (
        f'I found multiple requisitioners matching "{search_text}":\n'
        f"{lines}\n\n"
        "Please be more specific with a full name or employee number."
    )


def answer_catalog_tagged_requisitioners(user):
    scope_ids = scope_org_unit_ids_for_user(user)
    queryset = Employee.objects.filter(is_active=True)
    queryset = annotate_employee_reference_counts(queryset, scope_org_unit_ids=scope_ids)

    if scope_ids is not None:
        queryset = queryset.filter(scoped_referenced_document_count__gt=0).order_by(
            "-scoped_referenced_document_count",
            "last_name",
            "first_name",
        )
        get_count = lambda employee: employee.scoped_referenced_document_count
    else:
        queryset = queryset.filter(referenced_document_count__gt=0).order_by(
            "-referenced_document_count",
            "last_name",
            "first_name",
        )
        get_count = lambda employee: employee.referenced_document_count

    total = queryset.count()
    employees = list(queryset[: chatbot_list_limit()])
    if not employees:
        return {
            "answer": "I couldn't find any requisitioners with tagged documents in your accessible scope.",
            "matches": [],
            "audit_action": "CHATBOT_NO_RESULT",
        }

    lines = "\n".join(format_employee_summary(employee, get_count(employee)) for employee in employees)
    more_note = list_more_note(len(employees), total)
    browse_hint = (
        "\nUse the Requisitioners Directory page to browse the full list."
        if total > len(employees)
        else ""
    )
    return {
        "answer": (
            f"Requisitioners with tagged documents in your accessible scope:\n"
            f"{lines}{more_note}{browse_hint}"
        ),
        "matches": [],
        "audit_action": "CHATBOT_QUERY",
        **list_response_metadata(total, len(employees)),
    }


def answer_most_tagged_requisitioner(user):
    scope_ids = scope_org_unit_ids_for_user(user)
    queryset = Employee.objects.filter(is_active=True)
    queryset = annotate_employee_reference_counts(queryset, scope_org_unit_ids=scope_ids)

    if scope_ids is not None:
        queryset = queryset.filter(scoped_referenced_document_count__gt=0)
        count_field = "scoped_referenced_document_count"
        get_count = lambda employee: employee.scoped_referenced_document_count
    else:
        queryset = queryset.filter(referenced_document_count__gt=0)
        count_field = "referenced_document_count"
        get_count = lambda employee: employee.referenced_document_count

    top_count = (
        queryset.order_by(f"-{count_field}", "last_name", "first_name")
        .values_list(count_field, flat=True)
        .first()
    )
    if not top_count:
        return {
            "answer": "I couldn't find any requisitioners with tagged documents in your accessible scope.",
            "matches": [],
            "audit_action": "CHATBOT_NO_RESULT",
        }

    top_employees = list(
        queryset.filter(**{count_field: top_count}).order_by("last_name", "first_name")[
            : chatbot_list_limit()
        ]
    )
    if len(top_employees) == 1:
        employee = top_employees[0]
        return {
            "answer": (
                f"{employee.get_full_name()} "
                f"({format_employee_number_display(employee.employee_number)}) "
                f"has the most tagged documents: {get_count(employee)}."
            ),
            "matches": [],
            "audit_action": "CHATBOT_QUERY",
        }

    lines = "\n".join(
        format_employee_summary(employee, get_count(employee)) for employee in top_employees
    )
    label = pluralize_document(top_count)
    return {
        "answer": (
            f"These requisitioners are tied for the most tagged documents ({top_count} {label}):\n"
            f"{lines}"
        ),
        "matches": [],
        "audit_action": "CHATBOT_QUERY",
    }


def answer_find_requisitioner(user, query):
    search_text = extract_directory_search_text(query, FIND_REQUISITIONER_PATTERNS)
    if not search_text:
        search_text = clean_name(
            normalize_query(query).lower().replace("find requisitioner", "").strip()
        )
    if not search_text:
        return None

    employee, employees = resolve_single_employee(user, search_text)
    if not employee:
        if not employees:
            return {
                "answer": f'I couldn\'t find a requisitioner matching "{search_text}" in the directory.',
                "matches": [],
                "audit_action": "CHATBOT_NO_RESULT",
            }
        return {
            "answer": multiple_matches_answer(user, employees, search_text),
            "matches": [],
            "audit_action": "CHATBOT_QUERY",
        }

    count = tagged_count_for_user(user, employee)
    return {
        "answer": (
            f"Found requisitioner: {employee.get_full_name()} "
            f"({format_employee_number_display(employee.employee_number)})\n"
            f"Tagged Documents: {count}"
        ),
        "matches": [],
        "audit_action": "CHATBOT_QUERY",
    }


def answer_tagged_count(user, query):
    search_text = extract_directory_search_text(query, TAGGED_COUNT_PATTERNS)
    if not search_text:
        return None

    employee, employees = resolve_single_employee(user, search_text)
    if not employee:
        if not employees:
            return {
                "answer": f'I couldn\'t find a requisitioner matching "{search_text}" in the directory.',
                "matches": [],
                "audit_action": "CHATBOT_NO_RESULT",
            }
        return {
            "answer": multiple_matches_answer(user, employees, search_text),
            "matches": [],
            "audit_action": "CHATBOT_QUERY",
        }

    count = tagged_count_for_user(user, employee)
    scope_note = ""
    if getattr(user, "role", None) != "admin":
        scope_note = " in your accessible scope"
    return {
        "answer": (
            f"{employee.get_full_name()} "
            f"({format_employee_number_display(employee.employee_number)}) "
            f"is tagged on {count} {pluralize_document(count)}{scope_note}."
        ),
        "matches": [],
        "audit_action": "CHATBOT_QUERY",
    }


def answer_list_tagged_documents(user, query):
    search_text = extract_directory_search_text(query, LIST_TAGGED_PATTERNS)
    if not search_text:
        return None

    employee, employees = resolve_single_employee(user, search_text)
    if not employee:
        if not employees:
            return {
                "answer": f'I couldn\'t find a requisitioner matching "{search_text}" in the directory.',
                "matches": [],
                "audit_action": "CHATBOT_NO_RESULT",
            }
        return {
            "answer": multiple_matches_answer(user, employees, search_text),
            "matches": [],
            "audit_action": "CHATBOT_QUERY",
        }

    queryset = tagged_documents_for_user(user, employee)
    list_limit = chatbot_list_limit()
    total = queryset.count()
    documents = list(queryset.select_related("folder", "category")[:list_limit])
    if not documents:
        return {
            "answer": (
                f"{employee.get_full_name()} "
                f"({format_employee_number_display(employee.employee_number)}) "
                "has no tagged documents in your accessible scope."
            ),
            "matches": [],
            "audit_action": "CHATBOT_NO_RESULT",
        }

    lines = "\n".join(format_document_line(document) for document in documents)
    more_note = list_more_note(len(documents), total)
    browse_hint = (
        "\nUse the Requisitioners Directory page to view all tagged documents."
        if total > len(documents)
        else ""
    )
    return {
        "answer": (
            f"Documents tagged to {employee.get_full_name()} "
            f"({format_employee_number_display(employee.employee_number)}):\n"
            f"{lines}{more_note}{browse_hint}"
        ),
        "matches": document_matches(documents, "tagged document"),
        "audit_action": "CHATBOT_QUERY",
        **list_response_metadata(total, len(documents)),
    }


def answer_requisitioner_directory_intent(user, query):
    if not is_requisitioner_directory_query(query):
        return None

    if getattr(user, "role", None) == "staff":
        return {
            "answer": (
                "Requisitioners Directory information is available to administrators and department heads. "
                "Use document upload to search and tag requisitioners on your documents, "
                "or contact your department head or administrator for directory assistance."
            ),
            "matches": [],
            "audit_action": "CHATBOT_QUERY",
        }

    if getattr(user, "role", None) not in {"admin", "dept_head"}:
        return {
            "answer": (
                "Requisitioners Directory information is available to administrators and department heads. "
                "Use document upload to search and tag requisitioners on your documents, "
                "or contact your department head or administrator for directory assistance."
            ),
            "matches": [],
            "audit_action": "CHATBOT_QUERY",
        }

    normalized = normalize_query(query).lower()

    for pattern in MOST_TAGGED_PATTERNS:
        if pattern.search(normalized):
            return answer_most_tagged_requisitioner(user)

    for pattern in CATALOG_TAGGED_PATTERNS:
        if pattern.search(normalized):
            return answer_catalog_tagged_requisitioners(user)

    if "find requisitioner" in normalized:
        result = answer_find_requisitioner(user, query)
        if result:
            return result

    if any(term in normalized for term in ("list", "show")) and "tagged" in normalized:
        result = answer_list_tagged_documents(user, query)
        if result:
            return result

    if any(term in normalized for term in ("how many", "count", "number of")):
        result = answer_tagged_count(user, query)
        if result:
            return result

    if "tagged" in normalized:
        result = answer_list_tagged_documents(user, query) or answer_tagged_count(user, query)
        if result:
            return result

    return {
        "answer": (
            "I can answer Requisitioners Directory questions such as:\n"
            '- "How many documents is Ralph tagged on?"\n'
            '- "List documents tagged to Ralph"\n'
            '- "Find requisitioner D-2101-ASD"\n'
            '- "Which requisitioners have tagged documents?"\n'
            '- "Who has the most tagged documents?"'
        ),
        "matches": [],
        "audit_action": "CHATBOT_QUERY",
    }
