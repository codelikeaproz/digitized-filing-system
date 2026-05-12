from django.urls import path

from .views import DocumentAssistantChatAPIView, DocumentAssistantSearchPreviewAPIView


urlpatterns = [
    path("chat/", DocumentAssistantChatAPIView.as_view(), name="document-assistant-chat"),
    path("search-preview/", DocumentAssistantSearchPreviewAPIView.as_view(), name="document-assistant-search-preview"),
]
