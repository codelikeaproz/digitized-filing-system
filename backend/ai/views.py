from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from auditlogs.models import log_audit
from .serializers import ChatRequestSerializer, SearchPreviewSerializer
from .services.intent_service import answer_direct_intent, no_result_answer
from .services.llm_service import LLMServiceError, SAFE_LLM_FAILURE_RESPONSE, call_openrouter
from .services.prompt_service import SENSITIVE_REFUSAL, build_grounded_messages, contains_sensitive_request
from .services.search_service import search_accessible_documents, serialize_match


class DocumentAssistantChatAPIView(APIView):
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data["query"]
        session_id = serializer.validated_data.get("session_id") or None

        if contains_sensitive_request(query):
            log_audit(
                request.user,
                "CHATBOT_QUERY",
                "Denied sensitive assistant query.",
                target_type="DocumentAssistant",
                target_name="denied",
                target_org_unit=request.user.org_unit.name if getattr(request.user, "org_unit", None) else None,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            return Response({"answer": SENSITIVE_REFUSAL, "matches": []})

        direct_answer = answer_direct_intent(request.user, query)
        if direct_answer:
            matches = direct_answer.get("matches", [])
            log_audit(
                request.user,
                direct_answer.get("audit_action", "CHATBOT_QUERY"),
                f"Assistant direct intent processed. Query length: {len(query)}. Matched documents: {len(matches)}.",
                target_type="DocumentAssistant",
                target_name="direct",
                target_org_unit=request.user.org_unit.name if getattr(request.user, "org_unit", None) else None,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            return Response(
                {
                    "answer": direct_answer["answer"],
                    "matches": [serialize_match(match) for match in matches],
                }
            )

        matches = search_accessible_documents(request.user, query)
        serialized_matches = [serialize_match(match) for match in matches]

        if not matches:
            log_audit(
                request.user,
                "CHATBOT_NO_RESULT",
                f"Assistant query returned no accessible matches. Query length: {len(query)}",
                target_type="DocumentAssistant",
                target_name="no_result",
                target_org_unit=request.user.org_unit.name if getattr(request.user, "org_unit", None) else None,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            return Response({"answer": no_result_answer(), "matches": []})

        try:
            answer = call_openrouter(build_grounded_messages(query, matches), session_id=session_id)
            audit_action = "CHATBOT_QUERY"
        except LLMServiceError:
            answer = SAFE_LLM_FAILURE_RESPONSE
            audit_action = "CHATBOT_ERROR"

        log_audit(
            request.user,
            audit_action,
            f"Assistant query processed. Query length: {len(query)}. Matched documents: {len(matches)}.",
            target_type="DocumentAssistant",
            target_name="chat",
            target_org_unit=request.user.org_unit.name if getattr(request.user, "org_unit", None) else None,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response({"answer": answer, "matches": serialized_matches})


class DocumentAssistantSearchPreviewAPIView(APIView):
    def get(self, request):
        serializer = SearchPreviewSerializer(data={"q": request.query_params.get("q", "")})
        serializer.is_valid(raise_exception=True)
        matches = search_accessible_documents(request.user, serializer.validated_data["q"])
        return Response({"matches": [serialize_match(match) for match in matches]}, status=status.HTTP_200_OK)
