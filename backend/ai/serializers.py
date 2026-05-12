from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=1000, trim_whitespace=True)
    session_id = serializers.CharField(max_length=256, required=False, allow_blank=True, trim_whitespace=True)


class SearchPreviewSerializer(serializers.Serializer):
    q = serializers.CharField(max_length=1000, trim_whitespace=True)
