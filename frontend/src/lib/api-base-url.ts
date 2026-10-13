/**
 * Resolve a full API URL for browser requests.
 *
 * Production: relative path under the Vite base (e.g. /digifile/api/...)
 * so requests always use the same host/scheme as the loaded page.
 *
 * Development: absolute URL from VITE_API_URL (default http://127.0.0.1:8000).
 */
export function resolveApiUrl(endpoint: string): string {
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;

  if (import.meta.env.DEV) {
    const fromEnv = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
    return `${fromEnv}${cleanEndpoint}`;
  }

  const basePath = import.meta.env.BASE_URL.replace(/\/$/, "");
  if (basePath) {
    return `${basePath}${cleanEndpoint}`;
  }

  const fromEnv = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  return fromEnv ? `${fromEnv}${cleanEndpoint}` : cleanEndpoint;
}

/** Base path/origin for direct fetch calls (downloads, media URLs). */
export function getApiBaseUrl(): string {
  if (import.meta.env.DEV) {
    return (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  }

  const basePath = import.meta.env.BASE_URL.replace(/\/$/, "");
  if (basePath) {
    return basePath;
  }

  return (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
}
