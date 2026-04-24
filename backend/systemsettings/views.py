from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SystemSetting


def get_settings_object():
    obj, _ = SystemSetting.objects.get_or_create(pk=1)
    return obj


class SettingsView(APIView):
    def get(self, request):
        obj = get_settings_object()
        return Response(
            {
                "nasBasePath": obj.nas_base_path,
                "maxFileSize": obj.max_file_size,
                "autoArchive": obj.auto_archive,
            }
        )

    def put(self, request):
        obj = get_settings_object()
        obj.nas_base_path = request.data.get("nasBasePath", obj.nas_base_path)
        obj.max_file_size = request.data.get("maxFileSize", obj.max_file_size)
        obj.auto_archive = request.data.get("autoArchive", obj.auto_archive)
        obj.save()
        return self.get(request)
