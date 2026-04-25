from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    DashboardStatsAPIView,
    DocumentUploadView,
    DocumentViewSet,
    FolderViewSet,
    RecycleBinAPIView,
    RecycleBinDeleteAPIView,
    RecycleBinRestoreAPIView,
)

router = DefaultRouter(trailing_slash=False)
router.register("categories", CategoryViewSet, basename="category")
router.register("folders", FolderViewSet, basename="folder")
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("dashboard/stats", DashboardStatsAPIView.as_view(), name="dashboard-stats"),
    path("documents/upload", DocumentUploadView.as_view(), name="document-upload"),
    path(
        "documents/<int:pk>/download/",
        DocumentViewSet.as_view({"get": "download"}),
        name="document-download",
    ),
    path("recycle-bin", RecycleBinAPIView.as_view(), name="recycle-bin"),
    path("recycle-bin/restore", RecycleBinRestoreAPIView.as_view(), name="recycle-bin-restore"),
    path("recycle-bin/delete", RecycleBinDeleteAPIView.as_view(), name="recycle-bin-delete"),
] + router.urls
