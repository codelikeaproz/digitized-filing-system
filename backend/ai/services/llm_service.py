import json
import logging
import urllib.error
import urllib.request

from django.conf import settings


logger = logging.getLogger(__name__)
SAFE_LLM_FAILURE_RESPONSE = (
    "I found matching documents, but the AI summary is unavailable right now. "
    "Please check your internet connection or OpenRouter configuration, then try again."
)


class LLMServiceError(Exception):
    pass


def call_openrouter(messages, session_id=None):
    if not settings.OPENROUTER_API_KEY:
        raise LLMServiceError("OPENROUTER_API_KEY is not configured.")

    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.35,
        "max_tokens": 500,
    }
    if session_id:
        payload["session_id"] = session_id

    request = urllib.request.Request(
        f"{settings.OPENROUTER_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.FRONTEND_URL,
            "X-Title": "Digitized Filing System",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        logger.warning("OpenRouter HTTP error: %s %s", exc.code, detail[:500])
        raise LLMServiceError("OpenRouter request failed.") from exc
    except Exception as exc:
        logger.warning("OpenRouter request failed: %s", exc)
        raise LLMServiceError("OpenRouter request failed.") from exc

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("Unexpected OpenRouter response shape: %s", data)
        raise LLMServiceError("OpenRouter response was invalid.") from exc
