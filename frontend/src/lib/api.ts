/**
 * Centralized HTTP client for the DFS backend.
 *
 * Features:
 * - Attaches JWT from localStorage (auth_token)
 * - JSON helpers: get, post, put, patch, delete
 * - upload() for multipart/form-data (PDF uploads)
 * - Auto-redirect on 401 (logout), 429, 5xx
 *
 * Base URL: import.meta.env.VITE_API_URL
 *
 * @see docs/API_DOCUMENTATION.md
 */

const BASE_URL = import.meta.env.VITE_API_URL || "";

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | undefined | null>;
  skipRateLimitRedirect?: boolean;
}

class ApiService {
  private formatErrorPayload(data: any, fallback: string): string {
    if (typeof data?.error === "string" && data.error) return data.error;
    if (typeof data?.message === "string" && data.message) return data.message;
    if (typeof data?.detail === "string" && data.detail) return data.detail;
    if (Array.isArray(data?.detail) && data.detail.length) {
      return data.detail.map(String).join(", ");
    }
    if (data && typeof data === "object") {
      for (const value of Object.values(data)) {
        if (Array.isArray(value) && value.length) return String(value[0]);
        if (typeof value === "string" && value) return value;
      }
    }
    return fallback;
  }

  private getHeaders(): HeadersInit {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    const token = localStorage.getItem("auth_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    return headers;
  }

  async request<T>(endpoint: string, options: RequestOptions = {}, retries = 2): Promise<T> {
    const { params, ...init } = options;
    
    const cleanBaseUrl = BASE_URL.endsWith('/') ? BASE_URL.slice(0, -1) : BASE_URL;
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    let url = `${cleanBaseUrl}${cleanEndpoint}`;
    
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          searchParams.set(key, String(value));
        }
      });
      const query = searchParams.toString();
      if (query) url += `?${query}`;
    }

    try {
      const response = await fetch(url, {
        ...init,
        headers: {
          ...this.getHeaders(),
          ...init.headers,
        },
      });

      if (response.status === 401) {
        // Auto logout on unauthorized
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
        if (!window.location.pathname.startsWith("/login")) {
          window.location.href = "/login";
        }
        throw new Error("Unauthorized");
      }

      if (response.status === 429) {
        const text = await response.text();
        let data: any = {};
        try {
          data = text ? JSON.parse(text) : {};
        } catch {
          data = {};
        }

        const rateLimitError = new Error(
          data.message || data.detail || data.error || "Too many requests. Please wait before trying again."
        ) as Error & { status?: number };
        rateLimitError.status = 429;

        if (options.skipRateLimitRedirect) {
          throw rateLimitError;
        }

        if (!window.location.pathname.startsWith("/error/429")) {
          window.location.href = "/error/429";
        }
        throw rateLimitError;
      }

      if (response.status >= 500) {
        if (!window.location.pathname.startsWith("/error/500")) {
          window.location.href = "/error/500";
        }
        throw new Error("Internal Server Error");
      }

      const text = await response.text();
      let data: any = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        throw new Error("Server returned non-JSON response. Check API URL.");
      }

      if (!response.ok) {
        throw new Error(this.formatErrorPayload(data, `Request failed with status ${response.status}`));
      }

      return data;
    } catch (error: any) {
      if (retries > 0 && error.message === "Failed to fetch") {
        console.warn(`[API] Fetch failed, retrying... (${retries} left)`);
        await new Promise(r => setTimeout(r, 1000));
        return this.request<T>(endpoint, options, retries - 1);
      }
      throw error;
    }
  }

  get<T>(endpoint: string, params?: Record<string, string | number | undefined | null>) {
    return this.request<T>(endpoint, { method: "GET", params });
  }

  post<T>(
    endpoint: string,
    data?: any,
    options?: Pick<RequestOptions, "skipRateLimitRedirect">
  ) {
    return this.request<T>(endpoint, {
      method: "POST",
      body: JSON.stringify(data),
      ...options,
    });
  }

  put<T>(endpoint: string, data?: any) {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  patch<T>(endpoint: string, data?: any) {
    return this.request<T>(endpoint, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  delete<T>(endpoint: string) {
    return this.request<T>(endpoint, { method: "DELETE" });
  }

  requestPasswordReset(email: string) {
    return this.post<{ message: string }>("/api/auth/forgot-password/", { email });
  }

  resetPassword(data: any) {
    return this.post<{ message: string }>("/api/auth/reset-password/", data);
  }

  setPassword(data: any) {
    return this.post<{ message: string }>("/api/auth/set-password/", data);
  }

  // Specialized for FormData (Uploads)
  async upload<T>(endpoint: string, formData: FormData): Promise<T> {
    const headers = this.getHeaders() as Record<string, string>;
    delete headers["Content-Type"]; // Let fetch set boundary
    delete headers["content-type"];

    const cleanBaseUrl = BASE_URL.endsWith('/') ? BASE_URL.slice(0, -1) : BASE_URL;
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

    const response = await fetch(`${cleanBaseUrl}${cleanEndpoint}`, {
      method: "POST",
      body: formData,
      headers,
    });

    if (!response.ok) {
      const text = await response.text();
      let errorData: any = {};
      try {
        errorData = text ? JSON.parse(text) : {};
      } catch {
        errorData = {};
      }

      const message =
        errorData.message ||
        errorData.error ||
        errorData.detail ||
        text ||
        "Upload failed";
      throw new Error(message);
    }

    const contentType = response.headers.get("content-type");
    if (contentType && contentType.indexOf("application/json") !== -1) {
      return response.json();
    } else {
      const text = await response.text();
      throw new Error(`Server returned HTML instead of JSON: ${text.substring(0, 50)}...`);
    }
  }
}

export const api = new ApiService();
