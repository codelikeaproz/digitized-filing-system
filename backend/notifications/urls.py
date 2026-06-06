from django.urls import path

from .views import NotificationListAPIView, NotificationUnreadCountAPIView

urlpatterns = [
    path("", NotificationListAPIView.as_view(), name="notifications-list"),
    path("unread-count/", NotificationUnreadCountAPIView.as_view(), name="notifications-unread-count"),
]
