"""
Document Assistant API endpoints.

POST /api/ai/chat/           — natural-language queries over accessible documents
GET  /api/ai/search-preview/ — document match preview without LLM

Processing order:
    1. Sensitive-request guard
    2. Direct intent (counts, lists, greetings) via intent_service
    3. Document search + optional OpenRouter grounded answer

See CHATBOT_CAPABILITIES.md for supported query types.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from auditlogs.models import log_audit
from .serializers import ChatRequestSerializer, SearchPreviewSerializer
from .services.intent_service import answer_direct_intent, no_result_answer
from .services.page_context_service import apply_page_context_to_query, enrich_session_hints
from .services.llm_service import LLMServiceError, SAFE_LLM_FAILURE_RESPONSE, call_openrouter
from .services.prompt_service import SENSITIVE_REFUSAL, build_grounded_messages, contains_sensitive_request
from .services.search_service import (
    count_accessible_documents,
    is_list_request,
    search_accessible_documents,
    serialize_match,
)
from .throttles import ChatRateThrottle


def build_chat_response(answer, matches, *, total_matched=None, shown_count=None):
    payload = {
        "answer": answer,
        "matches": matches,
    }
    if total_matched is not None:
        payload["total_matched"] = total_matched
    if shown_count is not None:
        payload["shown_count"] = shown_count
    return payload


class DocumentAssistantChatAPIView(APIView):
    throttle_classes = [ChatRateThrottle]

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data["query"]
        session_id = serializer.validated_data.get("session_id") or None
        session_hints = enrich_session_hints(
            request.user,
            serializer.validated_data.get("session_hints") or {},
        )
        query = apply_page_context_to_query(query, session_hints)

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
            return Response(build_chat_response(SENSITIVE_REFUSAL, []))

        direct_answer = answer_direct_intent(request.user, query, session_hints=session_hints)
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
                build_chat_response(
                    direct_answer["answer"],
                    [serialize_match(match) for match in matches],
                    total_matched=direct_answer.get("total_matched"),
                    shown_count=direct_answer.get("shown_count"),
                )
            )

        matches = search_accessible_documents(request.user, query)
        serialized_matches = [serialize_match(match) for match in matches]
        total_matched = count_accessible_documents(request.user) if is_list_request(query) else None
        shown_count = len(serialized_matches) if total_matched is not None else None

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
            return Response(build_chat_response(no_result_answer(request.user, query), []))

        try:
            answer = call_openrouter(
                build_grounded_messages(query, matches, total_matched=total_matched),
                session_id=session_id,
            )
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
        return Response(
            build_chat_response(
                answer,
                serialized_matches,
                total_matched=total_matched,
                shown_count=shown_count,
            )
        )


class DocumentAssistantSearchPreviewAPIView(APIView):
    throttle_classes = [ChatRateThrottle]

    def get(self, request):
        serializer = SearchPreviewSerializer(data={"q": request.query_params.get("q", "")})
        serializer.is_valid(raise_exception=True)
        matches = search_accessible_documents(request.user, serializer.validated_data["q"])
        return Response({"matches": [serialize_match(match) for match in matches]}, status=status.HTTP_200_OK)
