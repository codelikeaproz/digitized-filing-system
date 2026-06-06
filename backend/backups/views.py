from django.http import FileResponse
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from auditlogs.models import log_audit

from .permissions import assert_backup_access
from .services import create_database_backup, create_media_backup, remove_backup_file


class BackupFileResponse(FileResponse):
    """Delete temporary backup files after the response is sent."""

    def __init__(self, backup_path, *args, **kwargs):
        self._backup_path = backup_path
        file_handle = open(backup_path, "rb")
        super().__init__(file_handle, *args, **kwargs)

    def close(self):
        super().close()
        remove_backup_file(self._backup_path)


class DatabaseBackupDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            assert_backup_access(
                request.user,
                backup_type="database",
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            backup_path, filename = create_database_backup()
        except PermissionDenied:
            raise
        except Exception as exc:
            raise APIException(str(exc)) from exc

        log_audit(
            request.user,
            "BACKUP_DATABASE_DOWNLOADED",
            f"Database backup downloaded ({filename})",
            target_type="Backup",
            target_name=filename,
            target_org_unit=getattr(getattr(request.user, "org_unit", None), "name", None),
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        response = BackupFileResponse(
            backup_path,
            as_attachment=True,
            filename=filename,
            content_type="application/sql",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class MediaBackupDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            assert_backup_access(
                request.user,
                backup_type="media",
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            backup_path, filename = create_media_backup()
        except PermissionDenied:
            raise
        except Exception as exc:
            raise APIException(str(exc)) from exc

        log_audit(
            request.user,
            "BACKUP_MEDIA_DOWNLOADED",
            f"Media backup downloaded ({filename})",
            target_type="Backup",
            target_name=filename,
            target_org_unit=getattr(getattr(request.user, "org_unit", None), "name", None),
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        response = BackupFileResponse(
            backup_path,
            as_attachment=True,
            filename=filename,
            content_type="application/zip",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
