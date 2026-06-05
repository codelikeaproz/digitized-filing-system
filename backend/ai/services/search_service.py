from dataclasses import dataclass
import re

from django.conf import settings
from django.db.models import Q

from documents.models import Document

from .chatbot_limits import chatbot_list_limit


MAX_EXCERPT_LENGTH = getattr(settings, "CHATBOT_EXCERPT_MAX_LENGTH", 1500)
MIN_BROAD_QUERY_LENGTH = 2
LIST_REQUEST_TERMS = {
    "all document",
    "all documents",
    "all file",
    "all files",
    "all record",
    "all records",
    "list document",
    "list documents",
    "list file",
    "list files",
    "list record",
    "list records",
    "show document",
    "show documents",
    "show file",
    "show files",
    "show record",
    "show records",
}
DOCUMENT_CODE_PATTERN = re.compile(r"\b[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+\b")


@dataclass
class DocumentMatch:
    document: Document
    score: int
    reasons: list[str]
    excerpt: str = ""


def org_unit_scope_ids(user):
    org_unit = getattr(user, "org_unit", None)
    if not org_unit:
        return []
    if getattr(user, "role", None) == "dept_head":
        return [org_unit.id, *[child.id for child in org_unit.get_all_children()]]
    return [org_unit.id]


def accessible_documents_for_user(user):
    queryset = Document.objects.filter(
        is_deleted=False,
        folder__is_deleted=False,
        folder__org_unit__is_deleted=False,
    ).select_related("folder", "folder__org_unit", "category").prefetch_related("requisitioners")

    if getattr(user, "role", None) == "admin":
        return queryset

    scoped_ids = org_unit_scope_ids(user)
    if not scoped_ids:
        return queryset.none()
    return queryset.filter(folder__org_unit_id__in=scoped_ids)


def normalize_query(query):
    return " ".join((query or "").strip().split())


def is_list_request(query):
    normalized = normalize_query(query).lower()
    if not normalized:
        return False
    return any(term in normalized for term in LIST_REQUEST_TERMS)


def extract_document_codes(query):
    return [match.group(0) for match in DOCUMENT_CODE_PATTERN.finditer(query or "")]


def contains(value, query):
    return query.lower() in (value or "").lower()


def safe_excerpt(text, query):
    if not text:
        return ""
    lowered = text.lower()
    needle = query.lower()
    index = lowered.find(needle)
    if index < 0:
        return text[:MAX_EXCERPT_LENGTH].strip()
    start = max(index - 180, 0)
    end = min(index + len(query) + 520, len(text))
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


def score_document(document, query):
    query_lower = query.lower()
    score = 0
    reasons = []

    code = document.code or ""
    title = document.title or ""
    file_name = document.file.name.rsplit("/", 1)[-1] if document.file else ""
    category = document.category.name if document.category else ""
    folder_path = document.folder.get_full_path() if document.folder else document.file_path
    description = document.description or ""
    keywords = [str(keyword) for keyword in (document.keywords or [])]
    extracted_text = document.extracted_text or ""
    requestor_display = document.requestor or ""

    if code and code.lower() == query_lower:
        score += 1000
        reasons.append("exact code")
    elif contains(code, query):
        score += 650
        reasons.append("code")

    if title.lower() == query_lower or file_name.lower() == query_lower:
        score += 850
        reasons.append("exact title")
    elif contains(title, query) or contains(file_name, query):
        score += 520
        reasons.append("title")

    if contains(category, query):
        score += 260
        reasons.append("category")
    if contains(folder_path, query):
        score += 260
        reasons.append("folder")
    if contains(description, query):
        score += 420
        reasons.append("description")
    for requisitioner in document.requisitioners.all():
        employee_number = requisitioner.employee_number or ""
        full_name = requisitioner.get_full_name()
        if employee_number and employee_number.lower() == query_lower:
            score += 920
            reasons.append("exact employee number")
        elif contains(employee_number, query):
            score += 600
            reasons.append("employee number")
        if full_name.lower() == query_lower:
            score += 820
            reasons.append("exact requisitioner name")
        elif contains(full_name, query):
            score += 540
            reasons.append("requisitioner")
    if contains(requestor_display, query):
        score += 480
        reasons.append("requestor")
    if any(contains(keyword, query) for keyword in keywords):
        score += 440
        reasons.append("keywords")
    if contains(extracted_text, query):
        score += 320
        reasons.append("document text")

    return score, reasons, safe_excerpt(extracted_text, query) if extracted_text and score else ""


def count_accessible_documents(user):
    return accessible_documents_for_user(user).count()


def search_accessible_documents(user, query, limit=None):
    if limit is None:
        limit = chatbot_list_limit()
    normalized = normalize_query(query)
    if not normalized:
        return []

    if is_list_request(normalized):
        documents = accessible_documents_for_user(user)[:limit]
        return [
            DocumentMatch(document=document, score=900, reasons=["accessible document"])
            for document in documents
        ]

    document_codes = extract_document_codes(normalized)
    if document_codes:
        code_filter = Q()
        for code in document_codes:
            code_filter |= Q(code__iexact=code)
        code_matches = accessible_documents_for_user(user).filter(code_filter)[:limit]
        return [
            DocumentMatch(
                document=document,
                score=1000,
                reasons=["exact code"],
                excerpt=safe_excerpt(document.extracted_text, normalized) or (document.extracted_text or "")[:MAX_EXCERPT_LENGTH],
            )
            for document in code_matches
        ]

    if len(normalized) < MIN_BROAD_QUERY_LENGTH:
        exact_code_matches = accessible_documents_for_user(user).filter(code__iexact=normalized)[:limit]
        return [
            DocumentMatch(document=document, score=1000, reasons=["exact code"])
            for document in exact_code_matches
        ]

    candidate_queryset = accessible_documents_for_user(user).filter(
        Q(code__icontains=normalized)
        | Q(title__icontains=normalized)
        | Q(file__icontains=normalized)
        | Q(category__name__icontains=normalized)
        | Q(folder__name__icontains=normalized)
        | Q(file_path__icontains=normalized)
        | Q(description__icontains=normalized)
        | Q(keywords__icontains=normalized)
        | Q(extracted_text__icontains=normalized)
        | Q(requestor__icontains=normalized)
        | Q(requisitioners__employee_number__icontains=normalized)
        | Q(requisitioners__first_name__icontains=normalized)
        | Q(requisitioners__last_name__icontains=normalized)
        | Q(requisitioners__suffix__icontains=normalized)
    ).distinct()[:80]

    matches = []
    for document in candidate_queryset:
        score, reasons, excerpt = score_document(document, normalized)
        if score > 0:
            matches.append(DocumentMatch(document=document, score=score, reasons=reasons, excerpt=excerpt))

    matches.sort(key=lambda match: (-match.score, match.document.title.lower()))
    return matches[:limit]


def serialize_match(match):
    document = match.document
    return {
        "id": document.id,
        "title": document.title,
        "code": document.code or "",
        "folder_id": str(document.folder_id) if document.folder_id else "",
        "folder_path": document.folder.get_full_path() if document.folder else document.file_path,
        "category": document.category.name if document.category else "",
        "org_unit": document.folder.org_unit.name if document.folder and document.folder.org_unit else "",
        "short_description": document.description or "",
        "keywords": document.keywords or [],
        "score": match.score,
        "reasons": match.reasons,
    }
