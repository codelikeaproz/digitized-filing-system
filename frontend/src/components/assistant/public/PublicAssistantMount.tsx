import { useLocation } from "react-router-dom";
import { PublicAssistant } from "./PublicAssistant";

const PUBLIC_ASSISTANT_PATHS = new Set([
  "/login",
  "/forgot-password",
  "/error/429",
  "/error/500",
]);

export function PublicAssistantMount() {
  const location = useLocation();

  if (!PUBLIC_ASSISTANT_PATHS.has(location.pathname)) {
    return null;
  }

  return <PublicAssistant />;
}
