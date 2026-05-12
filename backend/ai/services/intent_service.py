import re

from django.db.models import Q
from django.utils import timezone

from documents.models import Category, Folder
from .search_service import DocumentMatch, accessible_documents_for_user, org_unit_scope_ids


MAX_DIRECT_MATCHES = 5

COUNT_TERMS = {"how many", "count", "total number", "number of"}
DOCUMENT_TERMS = {"document", "documents", "file", "files", "record", "records"}
FOLDER_TERMS = {"folder", "folders"}
LIST_TERMS = {"list", "show", "find", "find all", "search", "all"}
REQUESTOR_TERMS = {"requestor", "requisitioner", "requested by", "request by"}
REQUESTOR_ALIASES = r"requestor|requisitioner|requestionaire|requisitionaire|requestioner|requester"
MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}
FOLDER_NAME_PATTERNS = [
    re.compile(r"\b(?:in|inside|under|within)\s+(.+?)\s+folder\b", re.IGNORECASE),
    re.compile(r"\bfolder\s+(?:named\s+|called\s+)?(.+)$", re.IGNORECASE),
    re.compile(r"\bfolder\s+of\s+(.+)$", re.IGNORECASE),
    re.compile(r"\bwhere\s+is\s+(.+?)\s+folder\b", re.IGNORECASE),
    re.compile(r"\bfind\s+(.+?)\s+folder\b", re.IGNORECASE),
]
REQUESTOR_PATTERNS = [
    re.compile(rf"\b(?:{REQUESTOR_ALIASES})\s+(?:named\s+|called\s+)?(.+)$", re.IGNORECASE),
    re.compile(r"\b(?:requested by|request by)\s+(.+)$", re.IGNORECASE),
    re.compile(rf"\b(?:find|show|search)\s+(.+?)\s+(?:{REQUESTOR_ALIASES})\b", re.IGNORECASE),
]
FILING_YEAR_PATTERN = re.compile(r"\bfiling\s+year\s+(20\d{2}|19\d{2})\b", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(20\d{2}|19\d{2})\b")
FILLER_WORDS = {
    "the",
    "a",
    "an",
    "my",
    "current",
    "available",
    "accessible",
    "all",
    "of",
    "named",
    "called",
    "file",
    "files",
    "document",
    "documents",
    "record",
    "records",
    "folder",
    "category",
}


def normalize_query(query):
    return " ".join((query or "").strip().split())


def has_any(normalized, terms):
    return any(term in normalized for term in terms)


def clean_name(value):
    words = [
        word
        for word in re.sub(r"[?.!,]+", " ", value or "").strip().split()
        if word.lower() not in FILLER_WORDS
    ]
    return " ".join(words).strip()


def pluralize_document(count):
    return "document" if count == 1 else "documents"


def accessible_folders_for_user(user):
    queryset = Folder.objects.filter(is_deleted=False, org_unit__is_deleted=False).select_related("org_unit", "parent")

    if getattr(user, "role", None) == "admin":
        return queryset

    scoped_ids = org_unit_scope_ids(user)
    if not scoped_ids:
        return queryset.none()
    return queryset.filter(org_unit_id__in=scoped_ids)


def extract_folder_name(query):
    normalized = normalize_query(query)
    for pattern in FOLDER_NAME_PATTERNS:
        match = pattern.search(normalized)
        if match:
            folder_name = clean_name(match.group(1))
            if folder_name:
                return folder_name
    return ""


def find_accessible_folders(user, folder_name, limit=MAX_DIRECT_MATCHES):
    if not folder_name:
        return []

    queryset = accessible_folders_for_user(user)
    exact_matches = list(queryset.filter(name__iexact=folder_name)[:limit])
    if exact_matches:
        return exact_matches
    return list(queryset.filter(name__icontains=folder_name)[:limit])


def find_accessible_category(user, query, excluded_names=None):
    normalized = normalize_query(query).lower()
    excluded = {name.lower() for name in (excluded_names or [])}
    categories = Category.objects.all()
    for category in categories:
        name = (category.name or "").strip()
        if name and name.lower() not in excluded and name.lower() in normalized:
            return category
    return None


def extract_requestor_name(query):
    normalized = normalize_query(query)
    for pattern in REQUESTOR_PATTERNS:
        match = pattern.search(normalized)
        if match:
            name = clean_name(match.group(1))
            if name:
                return name
    return ""


def date_label_and_filter(query):
    normalized = normalize_query(query).lower()
    now = timezone.localtime()

    if "today" in normalized:
        return "uploaded today", {"created_at__date": now.date()}

    if "this month" in normalized or "current month" in normalized:
        return f"uploaded in {now.strftime('%B %Y')}", {
            "created_at__year": now.year,
            "created_at__month": now.month,
        }

    if "this year" in normalized or "current year" in normalized:
        return f"uploaded in {now.year}", {"created_at__year": now.year}

    for month_name, month_number in MONTHS.items():
        if re.search(rf"\b{re.escape(month_name)}\b", normalized):
            year_match = YEAR_PATTERN.search(normalized)
            year = int(year_match.group(1)) if year_match else now.year
            label = f"uploaded in {timezone.datetime(year, month_number, 1).strftime('%B %Y')}"
            return label, {"created_at__year": year, "created_at__month": month_number}

    return "", {}


def filing_year_label_and_filter(query):
    match = FILING_YEAR_PATTERN.search(query or "")
    if not match:
        return "", {}
    year = int(match.group(1))
    return f"filing year {year}", {"filing_year": year}


def build_document_queryset(user, query, folders=None):
    queryset = accessible_documents_for_user(user)
    filters = []

    if folders is not None:
        queryset = queryset.filter(folder_id__in=[folder.id for folder in folders])
        if folders:
            filters.append(f"in {folders[0].get_full_path()}" if len(folders) == 1 else f"in {len(folders)} matching folders")

    category = find_accessible_category(user, query, excluded_names=[folder.name for folder in folders or []])
    if category:
        queryset = queryset.filter(category=category)
        filters.append(f"in {category.name} category")

    requestor_name = extract_requestor_name(query)
    if requestor_name:
        queryset = queryset.filter(requestor__icontains=requestor_name)
        filters.append(f"requested by {requestor_name}")

    filing_label, filing_filter = filing_year_label_and_filter(query)
    if filing_filter:
        queryset = queryset.filter(**filing_filter)
        filters.append(filing_label)
    else:
        date_label, date_filter = date_label_and_filter(query)
        if date_filter:
            queryset = queryset.filter(**date_filter)
            filters.append(date_label)

    return queryset, filters


def documents_in_folders(user, folders, limit=MAX_DIRECT_MATCHES):
    if not folders:
        return []
    queryset, _ = build_document_queryset(user, "", folders=folders)
    return list(queryset[:limit])


def document_matches(documents, reason):
    return [DocumentMatch(document=document, score=900, reasons=[reason]) for document in documents]


def format_document_line(document):
    category = document.category.name if document.category else "Uncategorized"
    folder_path = document.folder.get_full_path() if document.folder else document.file_path
    code = document.code or "No code"
    return f"- {document.title} (Code: {code}, Category: {category}, Folder: {folder_path})"


def format_folder_line(folder):
    org_unit = folder.org_unit.name if folder.org_unit else "No org unit"
    return f"- {folder.name} (Path: {folder.get_full_path()}, Org Unit: {org_unit})"


def answer_direct_intent(user, query):
    normalized_query = normalize_query(query)
    normalized = normalized_query.lower()
    if not normalized:
        return None

    asks_count = has_any(normalized, COUNT_TERMS)
    mentions_document = has_any(normalized, DOCUMENT_TERMS)
    mentions_folder = has_any(normalized, FOLDER_TERMS)
    asks_list = has_any(normalized, LIST_TERMS)
    folder_name = extract_folder_name(normalized_query)
    has_filter = bool(
        folder_name
        or find_accessible_category(user, normalized_query)
        or extract_requestor_name(normalized_query)
        or date_label_and_filter(normalized_query)[1]
        or filing_year_label_and_filter(normalized_query)[1]
    )

    if asks_count and mentions_document and folder_name:
        folders = find_accessible_folders(user, folder_name)
        if not folders:
            return {
                "answer": f"I couldn't find an accessible folder named \"{folder_name}\".",
                "matches": [],
                "audit_action": "CHATBOT_NO_RESULT",
            }

        queryset, filters = build_document_queryset(user, normalized_query, folders=folders)
        count = queryset.count()
        folder_label = ", ".join(filters) if filters else (folders[0].get_full_path() if len(folders) == 1 else f"{len(folders)} matching folders")
        return {
            "answer": f"{folder_label} contains {count} accessible {pluralize_document(count)}.",
            "matches": [],
            "audit_action": "CHATBOT_QUERY",
        }

    if asks_count and (mentions_document or has_filter):
        queryset, filters = build_document_queryset(user, normalized_query)
        count = queryset.count()
        scope = ", ".join(filters)
        answer = (
            f"You currently have {count} accessible {pluralize_document(count)} matching {scope}."
            if scope
            else f"You currently have {count} accessible {pluralize_document(count)}."
        )
        return {
            "answer": answer,
            "matches": [],
            "audit_action": "CHATBOT_QUERY",
        }

    if mentions_folder and not mentions_document:
        folders = find_accessible_folders(user, folder_name or clean_name(normalized_query.replace("folder", "")))
        if folders:
            lines = "\n".join(format_folder_line(folder) for folder in folders)
            return {
                "answer": f"I found these accessible folder match{'es' if len(folders) != 1 else ''}:\n{lines}",
                "matches": [],
                "audit_action": "CHATBOT_QUERY",
            }

    if asks_list and mentions_document and folder_name:
        folders = find_accessible_folders(user, folder_name)
        if not folders:
            return {
                "answer": f"I couldn't find an accessible folder named \"{folder_name}\".",
                "matches": [],
                "audit_action": "CHATBOT_NO_RESULT",
            }
        queryset, filters = build_document_queryset(user, normalized_query, folders=folders)
        documents = list(queryset[:MAX_DIRECT_MATCHES])
        if not documents:
            return {
                "answer": f"I found the folder, but it has no accessible documents for that filter.",
                "matches": [],
                "audit_action": "CHATBOT_NO_RESULT",
            }
        lines = "\n".join(format_document_line(document) for document in documents)
        filter_label = ", ".join(filters) if filters else folders[0].get_full_path()
        return {
            "answer": f"Here are documents I found {filter_label}:\n{lines}",
            "matches": document_matches(documents, "folder document"),
            "audit_action": "CHATBOT_QUERY",
        }

    if asks_list and (mentions_document or has_filter):
        queryset, filters = build_document_queryset(user, normalized_query)
        documents = list(queryset[:MAX_DIRECT_MATCHES])
        if not documents:
            return {
                "answer": "I couldn't find accessible documents for that filter.",
                "matches": [],
                "audit_action": "CHATBOT_NO_RESULT",
            }
        lines = "\n".join(format_document_line(document) for document in documents)
        scope = f" matching {', '.join(filters)}" if filters else ""
        total = queryset.count()
        more_note = f"\nShowing {len(documents)} of {total}." if total > len(documents) else ""
        return {
            "answer": f"Here are the first {len(documents)} accessible {pluralize_document(len(documents))}{scope} I found:\n{lines}{more_note}",
            "matches": document_matches(documents, "accessible document"),
            "audit_action": "CHATBOT_QUERY",
        }

    return None


def no_result_answer():
    return (
        "I couldn't find a matching document in your accessible scope.\n\n"
        "Try asking by document code, title, folder, category, keyword, or PDF content. "
        "Examples: \"list all documents\", \"how many files do I have?\", "
        "\"show documents in Test folder\", or \"what is inside code 01-12551?\""
    )
