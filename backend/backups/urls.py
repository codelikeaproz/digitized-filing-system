from django.urls import path

from .views import DatabaseBackupDownloadView, MediaBackupDownloadView

urlpatterns = [
    path("backups/database", DatabaseBackupDownloadView.as_view(), name="backup-database"),
    path("backups/media", MediaBackupDownloadView.as_view(), name="backup-media"),
]
