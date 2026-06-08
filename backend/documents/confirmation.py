"""Typed confirmation helpers for irreversible recycle-bin deletions."""


def build_permanent_delete_confirmation(display_name: str) -> str:
    return f"DELETE {display_name.strip()}"


def validate_permanent_delete_confirmation(provided: str | None, expected: str) -> bool:
    if provided is None:
        return False
    return provided == expected


def build_bulk_permanent_delete_confirmation(item_count: int) -> str:
    label = "ITEM" if item_count == 1 else "ITEMS"
    return f"DELETE {item_count} {label}"
