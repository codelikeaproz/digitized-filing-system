"""
Document app URL routes.

Registers ViewSets (categories, folders, documents) and standalone views for
upload, recycle bin, and dashboard stats.

Router uses trailing_slash=False — paths are /api/documents not /api/documents/
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    DashboardStatsAPIView,
    DocumentNextCodeAPIView,
    DocumentUploadView,
    DocumentViewSet,
    FolderViewSet,
    RecycleBinAPIView,
    RecycleBinBulkDeleteAPIView,
    RecycleBinBulkRestoreAPIView,
    RecycleBinBulkSummaryAPIView,
    RecycleBinDeleteAPIView,
    RecycleBinRestoreAPIView,
)

router = DefaultRouter(trailing_slash=False)
router.register("categories", CategoryViewSet, basename="category")
router.register("folders", FolderViewSet, basename="folder")
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("dashboard/", DashboardStatsAPIView.as_view(), name="dashboard"),
    path("dashboard/stats", DashboardStatsAPIView.as_view(), name="dashboard-stats"),
    path("documents/upload", DocumentUploadView.as_view(), name="document-upload"),
    path("documents/next-code", DocumentNextCodeAPIView.as_view(), name="document-next-code"),
    path(
        "documents/<int:pk>/download/",
        DocumentViewSet.as_view({"get": "download"}),
        name="document-download",
    ),
    path("recycle-bin", RecycleBinAPIView.as_view(), name="recycle-bin"),
    path("recycle-bin/restore", RecycleBinRestoreAPIView.as_view(), name="recycle-bin-restore"),
    path("recycle-bin/delete", RecycleBinDeleteAPIView.as_view(), name="recycle-bin-delete"),
    path("recycle-bin/bulk-summary", RecycleBinBulkSummaryAPIView.as_view(), name="recycle-bin-bulk-summary"),
    path("recycle-bin/bulk-restore", RecycleBinBulkRestoreAPIView.as_view(), name="recycle-bin-bulk-restore"),
    path("recycle-bin/bulk-delete", RecycleBinBulkDeleteAPIView.as_view(), name="recycle-bin-bulk-delete"),
]

urlpatterns += router.urls
