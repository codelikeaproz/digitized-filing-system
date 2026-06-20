"""
Root URL configuration for the DFS API.

Mounts:
    /api/           — accounts, orgunits, auditlogs, documents
    /api/ai/        — document assistant
    /api/token/     — SimpleJWT obtain + refresh
    /media/         — uploaded PDFs (development)
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("orgunits.urls")),
    path("api/", include("auditlogs.urls")),
    path("api/", include("backups.urls")),
    path("api/system/", include("system.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/", include("documents.urls")),
    path("api/", include("employees.urls")),
    path("api/ai/", include("ai.urls")),
    path('api/token/', TokenObtainPairView.as_view(), name="get_token"),
    path('api/token/refresh/', TokenRefreshView.as_view(), name="refresh"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path('api-auth/', include('rest_framework.urls')),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
