from rest_framework import serializers


class ChatSessionHintsSerializer(serializers.Serializer):
    recent_greeting = serializers.BooleanField(required=False, default=False)
    recent_help = serializers.BooleanField(required=False, default=False)
    folder_id = serializers.CharField(required=False, allow_blank=True)
    folder_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    category_id = serializers.CharField(required=False, allow_blank=True)
    category_name = serializers.CharField(required=False, allow_blank=True, max_length=100)


class ChatRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=1000, trim_whitespace=True)
    session_id = serializers.CharField(max_length=256, required=False, allow_blank=True, trim_whitespace=True)
    session_hints = ChatSessionHintsSerializer(required=False)


class SearchPreviewSerializer(serializers.Serializer):
    q = serializers.CharField(max_length=1000, trim_whitespace=True)
