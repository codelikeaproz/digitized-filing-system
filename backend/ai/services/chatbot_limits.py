from django.conf import settings


BROWSE_FULL_LIST_HINT = "Use the Documents page to browse the full list."


def chatbot_list_limit():
    return int(getattr(settings, "CHATBOT_LIST_LIMIT", 5))
