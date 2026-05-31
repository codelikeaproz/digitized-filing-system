import re

from .intent_service import DOCUMENT_TERMS, COUNT_TERMS, LIST_TERMS, accessible_folders_for_user, has_any, normalize_query


def enrich_session_hints(user, session_hints=None):
    hints = dict(session_hints or {})
    folder_id = (hints.get("folder_id") or "").strip()
    if folder_id and not (hints.get("folder_name") or "").strip():
        folder = accessible_folders_for_user(user).filter(pk=folder_id).first()
        if folder:
            hints["folder_name"] = folder.name

    category_name = (hints.get("category_name") or "").strip()
    category_id = (hints.get("category_id") or "").strip()
    if category_id and not category_name:
        from documents.models import Category

        category = Category.objects.filter(pk=category_id).first()
        if category:
            hints["category_name"] = category.name

    return hints


def apply_page_context_to_query(query, session_hints=None):
    hints = session_hints or {}
    folder_name = (hints.get("folder_name") or "").strip()
    category_name = (hints.get("category_name") or "").strip()
    if not folder_name and not category_name:
        return query

    result = query
    normalized = normalize_query(query).lower()
    mentions_documents = (
        has_any(normalized, DOCUMENT_TERMS)
        or has_any(normalized, LIST_TERMS)
        or has_any(normalized, COUNT_TERMS)
    )

    if folder_name:
        folder_replacements = [
            (r"\bthis folder\b", f"{folder_name} folder"),
            (r"\bthe current folder\b", f"{folder_name} folder"),
            (r"\bcurrent folder\b", f"{folder_name} folder"),
            (r"\bin this folder\b", f"in {folder_name} folder"),
            (r"\bin the current folder\b", f"in {folder_name} folder"),
            (r"\ball files in this folder\b", f"all files in {folder_name} folder"),
            (r"\bshow all documents here\b", f"show all documents in {folder_name} folder"),
            (
                r"\blist everything in the current folder\b",
                f"list all documents in {folder_name} folder",
            ),
        ]
        for pattern, replacement in folder_replacements:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        if mentions_documents and re.search(r"\b(here|in here)\b", result, re.IGNORECASE):
            result = re.sub(r"\bin here\b", f"in {folder_name} folder", result, flags=re.IGNORECASE)
            result = re.sub(r"\bhere\b", f"in {folder_name} folder", result, flags=re.IGNORECASE)

    if category_name:
        category_replacements = [
            (r"\bthis category\b", f"{category_name} category"),
            (r"\bthe current category\b", f"{category_name} category"),
            (r"\bcurrent category\b", f"{category_name} category"),
            (r"\bin this category\b", f"in {category_name} category"),
        ]
        for pattern, replacement in category_replacements:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result
