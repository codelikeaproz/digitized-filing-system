from django.conf import settings


class AllowMediaIframeMiddleware:
    """Allow local media files to render inside the React PDF preview iframe."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(settings.MEDIA_URL):
            response.headers.pop("X-Frame-Options", None)
        return response
