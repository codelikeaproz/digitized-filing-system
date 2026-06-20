import { resolveApiUrl } from "@/lib/api-base-url";
import { appPath, isAppPath } from "@/lib/app-path";
import { clearAuthStorage, getRefreshToken, setAuthTokens } from "@/lib/auth-storage";

let refreshPromise: Promise<boolean> | null = null;

export async function refreshAccessToken(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;

  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const response = await fetch(resolveApiUrl("/api/token/refresh/"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ refresh }),
      });

      if (!response.ok) return false;

      const data = await response.json();
      if (typeof data.access !== "string") return false;

      setAuthTokens(data.access, typeof data.refresh === "string" ? data.refresh : null);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export function redirectToLogin() {
  clearAuthStorage();
  if (!isAppPath("/login")) {
    window.location.href = appPath("/login");
  }
}
