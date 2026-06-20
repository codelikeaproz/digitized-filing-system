"""
Direct intent handling for the Document Assistant.

Parses structured user queries (counts, lists, greetings, filters) without
calling the LLM. Returns None when the query should fall through to search/LLM.

Also provides contextual empty-state messages when folders/org units have
no documents yet.
"""
import re

from django.db.models import Q
from django.utils import timezone

from documents.models import Category, Folder
from documents.permissions import org_unit_scope_ids
from orgunits.models import OrgUnit
from .chatbot_limits import BROWSE_FULL_LIST_HINT, chatbot_list_limit
from .search_service import DocumentMatch, accessible_documents_for_user, is_list_request


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
GREETING_PHRASES = {
    "hi",
    "hello",
    "hey",
    "howdy",
    "hi there",
    "hello there",
    "hey there",
    "good morning",
    "good afternoon",
    "good evening",
}
HELP_PHRASES = {
    "help",
    "what can you do",
    "what do you do",
    "how can you help",
    "how can you help me",
}

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


def strip_trailing_punctuation(value):
    return re.sub(r"[!?.…,;:]+$", "", (value or "").strip())


def is_greeting_query(query):
    cleaned = strip_trailing_punctuation(normalize_query(query).lower())
    if not cleaned:
        return False
    if cleaned in GREETING_PHRASES:
        return True
    parts = [strip_trailing_punctuation(part.strip()) for part in re.split(r"[,;/]+", cleaned) if part.strip()]
    return bool(parts) and all(part in GREETING_PHRASES for part in parts)


def is_help_query(query):
    cleaned = strip_trailing_punctuation(normalize_query(query).lower())
    return cleaned in HELP_PHRASES


def greeting_answer(user, *, repeat=False):
    if repeat:
        return "Hi again! Ask about a document code, folder, or say \"help\" for options."
    display_name = (getattr(user, "get_full_name", lambda: "")() or "").strip()
    salutation = f"Hi {display_name}!" if display_name else "Hi!"
    return (
        f"{salutation} I'm the Document Assistant for the Digitized Filing System. "
        "I can help you find and explore documents within your access scope.\n\n"
        "Try asking:\n"
        '- "How many files do I have?"\n'
        '- "List all documents"\n'
        '- "Show documents in Test folder"\n'
        '- "Find document code TEST-101"'
    )


def help_answer(*, repeat=False):
    if repeat:
        return (
            "Try a document code, folder name, or ask \"how many files do I have?\" "
            "Say \"list all documents\" to preview up to 5 files in your access scope."
        )
    return (
        "I can help with document tasks inside your access scope:\n"
        "- Count documents (overall, by folder, category, date, or filing year)\n"
        "- List accessible documents or documents in a folder (up to 5 at a time)\n"
        "- Find folders by name\n"
        "- Search by document code, title, keyword, requisitioner, or PDF text\n"
        "- Answer Requisitioners Directory questions (tagged counts and tagged document lists)\n"
        "- Answer questions about a specific document's content\n\n"
        "Examples: \"list all documents\", \"how many files in Test folder\", "
        "\"how many documents is Ralph tagged on?\", "
        "\"find code TEST-101\", or \"summarize the RRL document\"."
    )


def list_more_note(shown_count, total):
    if total <= shown_count:
        return ""
    return f"\nShowing {shown_count} of {total}.\n{BROWSE_FULL_LIST_HINT}"


def list_response_metadata(total, shown):
    return {
        "total_matched": total,
        "shown_count": shown,
    }


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


def find_accessible_folders(user, folder_name, limit=None):
    if limit is None:
        limit = chatbot_list_limit()
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
        queryset = queryset.filter(
            Q(requisitioners__first_name__icontains=requestor_name)
            | Q(requisitioners__last_name__icontains=requestor_name)
            | Q(requisitioners__suffix__icontains=requestor_name)
            | Q(requisitioners__employee_number__icontains=requestor_name)
            | Q(requestor__icontains=requestor_name)
        ).distinct()
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


def documents_in_folders(user, folders, limit=None):
    if limit is None:
        limit = chatbot_list_limit()
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


def has_extra_filters(user, query, folders=None):
    excluded = [folder.name for folder in folders or []]
    return bool(
        find_accessible_category(user, query, excluded_names=excluded)
        or extract_requestor_name(query)
        or date_label_and_filter(query)[1]
        or filing_year_label_and_filter(query)[1]
    )


def scope_has_documents(user, folders=None):
    queryset = accessible_documents_for_user(user)
    if folders:
        queryset = queryset.filter(folder_id__in=[folder.id for folder in folders])
    return queryset.exists()


def empty_folder_answer(folder):
    label = folder.get_full_path()
    return (
        f'The "{label}" folder is currently empty.\n\n'
        "Please upload PDF documents to this folder in the Documents area."
    )


def no_documents_in_scope_answer(user):
    role = getattr(user, "role", None)
    org_unit = getattr(user, "org_unit", None)

    if role == "admin":
        if not OrgUnit.objects.filter(is_deleted=False).exists():
            return (
                "There are no organization units set up yet.\n\n"
                "Please create an org unit in Organization Units, then add folders and upload documents."
            )
        if not accessible_folders_for_user(user).exists():
            return (
                "There are organization units, but no folders yet.\n\n"
                "Please create folders first, then upload PDF documents in the Documents area."
            )
        return (
            "There are no documents in the system yet.\n\n"
            "Please upload PDF files through the Documents area."
        )

    if not org_unit:
        return (
            "Your account is not assigned to an organization unit yet.\n\n"
            "Please contact your administrator to assign your department or org unit."
        )

    org_name = org_unit.name
    if not accessible_folders_for_user(user).exists():
        return (
            f"Your organization unit ({org_name}) has no folders yet.\n\n"
            "Please create a folder first, then upload PDF documents in the Documents area."
        )

    return (
        "There are no documents in your accessible scope yet.\n\n"
        "Please upload PDF files to a folder in the Documents area."
    )


def empty_documents_answer(user, *, filters=None, folders=None, query=None):
    filters = filters or []
    query = query or ""

    if folders:
        folder_label = (
            folders[0].get_full_path()
            if len(folders) == 1
            else f"{len(folders)} matching folders"
        )
        if has_extra_filters(user, query, folders):
            if scope_has_documents(user, folders):
                scope = ", ".join(filters) if filters else "that filter"
                return (
                    f'I found the folder "{folder_label}", '
                    f"but no accessible documents match {scope}."
                )
            if len(folders) == 1:
                return empty_folder_answer(folders[0])
            return (
                "The selected folders have no documents yet.\n\n"
                "Please upload PDF documents in the Documents area."
            )
        if len(folders) == 1:
            return empty_folder_answer(folders[0])
        return (
            "The selected folders have no documents yet.\n\n"
            "Please upload PDF documents in the Documents area."
        )

    if filters:
        if scope_has_documents(user):
            scope = ", ".join(filters)
            return f"I couldn't find accessible documents matching {scope}."
        return no_documents_in_scope_answer(user)

    return no_documents_in_scope_answer(user)


def answer_direct_intent(user, query, session_hints=None):
    normalized_query = normalize_query(query)
    normalized = normalized_query.lower()
    if not normalized:
        return None

    hints = session_hints or {}

    if is_greeting_query(normalized_query):
        return {
            "answer": greeting_answer(user, repeat=bool(hints.get("recent_greeting"))),
            "matches": [],
            "audit_action": "CHATBOT_QUERY",
        }

    if is_help_query(normalized_query):
        return {
            "answer": help_answer(repeat=bool(hints.get("recent_help"))),
            "matches": [],
            "audit_action": "CHATBOT_QUERY",
        }

    from .requisitioner_directory_service import answer_requisitioner_directory_intent

    directory_answer = answer_requisitioner_directory_intent(user, normalized_query)
    if directory_answer:
        return directory_answer

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
        if count == 0:
            return {
                "answer": empty_documents_answer(
                    user,
                    filters=filters,
                    folders=folders,
                    query=normalized_query,
                ),
                "matches": [],
                "audit_action": "CHATBOT_NO_RESULT",
            }
        folder_label = ", ".join(filters) if filters else (folders[0].get_full_path() if len(folders) == 1 else f"{len(folders)} matching folders")
        return {
            "answer": f"{folder_label} contains {count} accessible {pluralize_document(count)}.",
            "matches": [],
            "audit_action": "CHATBOT_QUERY",
        }

    if asks_count and (mentions_document or has_filter):
        queryset, filters = build_document_queryset(user, normalized_query)
        count = queryset.count()
        if count == 0:
            return {
                "answer": empty_documents_answer(
                    user,
                    filters=filters,
                    query=normalized_query,
                ),
                "matches": [],
                "audit_action": "CHATBOT_NO_RESULT",
            }
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
        list_limit = chatbot_list_limit()
        total = queryset.count()
        documents = list(queryset[:list_limit])
        if not documents:
            return {
                "answer": empty_documents_answer(
                    user,
                    filters=filters,
                    folders=folders,
                    query=normalized_query,
                ),
                "matches": [],
                "audit_action": "CHATBOT_NO_RESULT",
            }
        lines = "\n".join(format_document_line(document) for document in documents)
        filter_label = ", ".join(filters) if filters else folders[0].get_full_path()
        if total > len(documents):
            answer = (
                f"{filter_label} has {total} accessible {pluralize_document(total)}.\n"
                f"Showing {len(documents)} of {total}:\n{lines}\n{BROWSE_FULL_LIST_HINT}"
            )
        else:
            answer = f"Here are documents I found {filter_label}:\n{lines}"
        return {
            "answer": answer,
            "matches": document_matches(documents, "folder document"),
            "audit_action": "CHATBOT_QUERY",
            **list_response_metadata(total, len(documents)),
        }

    if asks_list and (mentions_document or has_filter):
        queryset, filters = build_document_queryset(user, normalized_query)
        list_limit = chatbot_list_limit()
        total = queryset.count()
        documents = list(queryset[:list_limit])
        if not documents:
            return {
                "answer": empty_documents_answer(
                    user,
                    filters=filters,
                    query=normalized_query,
                ),
                "matches": [],
                "audit_action": "CHATBOT_NO_RESULT",
            }
        lines = "\n".join(format_document_line(document) for document in documents)
        scope = f" matching {', '.join(filters)}" if filters else ""
        more_note = list_more_note(len(documents), total)
        return {
            "answer": f"Here are the first {len(documents)} accessible {pluralize_document(len(documents))}{scope} I found:\n{lines}{more_note}",
            "matches": document_matches(documents, "accessible document"),
            "audit_action": "CHATBOT_QUERY",
            **list_response_metadata(total, len(documents)),
        }

    return None


def no_result_answer(user=None, query=None):
    if user is not None and query and is_list_request(query) and not scope_has_documents(user):
        return no_documents_in_scope_answer(user)

    return (
        "I couldn't find a matching document in your accessible scope.\n\n"
        "Try asking by document code, title, folder, category, keyword, requisitioner, or PDF content. "
        "Examples: \"list all documents\", \"how many files do I have?\", "
        "\"show documents in Test folder\", or \"find code TEST-101\""
    )
