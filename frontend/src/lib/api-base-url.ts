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

/**
 * Resolve a document media URL for iframe preview.
 *
 * Django returns absolute URLs like https://host/media/... which miss the
 * production subpath (/digifile). Always route media through getApiBaseUrl().
 */
export function resolveMediaUrl(fileUrl?: string | null): string | null {
  if (!fileUrl) return null;

  const base = getApiBaseUrl().replace(/\/$/, "");

  const withBase = (pathname: string, search = "", hash = "") => {
    const path = pathname.startsWith("/") ? pathname : `/${pathname}`;
    if (base && (path === base || path.startsWith(`${base}/`))) {
      return `${path}${search}${hash}`;
    }
    return `${base}${path}${search}${hash}`;
  };

  if (fileUrl.startsWith("/")) {
    return withBase(fileUrl);
  }

  try {
    const url = new URL(fileUrl);
    return withBase(url.pathname, url.search, url.hash);
  } catch {
    return withBase(fileUrl.replace(/^\/+/, ""));
  }
}
