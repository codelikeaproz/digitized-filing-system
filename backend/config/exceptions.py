from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, Throttled) and response is not None:
        response.data = {
            "error": "Too Many Requests",
            "message": "Too many login attempts. Please try again shortly.",
        }

    return response
