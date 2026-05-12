const DOCUMENT_ASSISTANT_OPENROUTER_SESSION_KEY = "dfs_document_assistant_openrouter_session_id";

const DOCUMENT_ASSISTANT_SESSION_KEYS = [
  "dfs_document_assistant_messages",
  "dfs_document_assistant_matches",
  "dfs_document_assistant_context",
  DOCUMENT_ASSISTANT_OPENROUTER_SESSION_KEY,
];

function createSessionId() {
  const randomId =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;

  return `dfs-document-assistant-${randomId}`;
}

export function getDocumentAssistantOpenRouterSessionId() {
  const existingSessionId = sessionStorage.getItem(DOCUMENT_ASSISTANT_OPENROUTER_SESSION_KEY);
  if (existingSessionId) return existingSessionId;

  const sessionId = createSessionId();
  sessionStorage.setItem(DOCUMENT_ASSISTANT_OPENROUTER_SESSION_KEY, sessionId);
  return sessionId;
}

export function clearDocumentAssistantSession() {
  DOCUMENT_ASSISTANT_SESSION_KEYS.forEach((key) => {
    sessionStorage.removeItem(key);
    localStorage.removeItem(key);
  });
}
