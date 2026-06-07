from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


def notifications_for_user(user):
    is_admin = getattr(user, "role", None) == "admin"
    audience_filter = Q(audience=Notification.AUDIENCE_ALL)
    if is_admin:
        audience_filter |= Q(audience=Notification.AUDIENCE_ADMIN)
    return Notification.objects.filter(audience_filter)


class NotificationListAPIView(APIView):
    def get(self, request):
        queryset = notifications_for_user(request.user)[:50]
        return Response(NotificationSerializer(queryset, many=True).data)


class NotificationUnreadCountAPIView(APIView):
    def get(self, request):
        count = notifications_for_user(request.user).count()
        return Response({"count": count})


class NotificationClearAPIView(APIView):
    def post(self, request):
        deleted, _ = notifications_for_user(request.user).delete()
        return Response({"deleted": deleted})
