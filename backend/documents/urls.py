"""
Document app URL routes.

Registers ViewSets (categories, folders, documents) and standalone views for
upload, recycle bin, dashboard stats, and scanner bridge endpoints.

Router uses trailing_slash=False — paths are /api/documents not /api/documents/
"""
from django.conf import settings
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
    PendingScanJobAPIView,
    ScanJobDetailAPIView,
    ScanJobFailAPIView,
    ScanJobListCreateAPIView,
    ScanJobUploadAPIView,
    ScannerStationHeartbeatAPIView,
    ScannerStationListAPIView,
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
]

# Scanner Bridge routes are optional. Keep them disabled in environments where
# Epson/bridge integration is not deployed yet.
if settings.ENABLE_SCANNER_FEATURE:
    urlpatterns += [
        path("scanner/stations", ScannerStationListAPIView.as_view(), name="scanner-stations"),
        path("scanner/stations/heartbeat", ScannerStationHeartbeatAPIView.as_view(), name="scanner-heartbeat"),
        path("scan-jobs", ScanJobListCreateAPIView.as_view(), name="scan-jobs"),
        path("scan-jobs/pending", PendingScanJobAPIView.as_view(), name="scan-job-pending"),
        path("scan-jobs/<int:pk>", ScanJobDetailAPIView.as_view(), name="scan-job-detail"),
        path("scan-jobs/<int:pk>/upload", ScanJobUploadAPIView.as_view(), name="scan-job-upload"),
        path("scan-jobs/<int:pk>/fail", ScanJobFailAPIView.as_view(), name="scan-job-fail"),
    ]

urlpatterns += router.urls
