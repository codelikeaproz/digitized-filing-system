/**
 * Authentication context — session state for the SPA.
 *
 * On load: restores the session through the HttpOnly refresh cookie.
 * Login:   POST /api/auth/login → keeps the access token in memory.
 * Logout:  clears the refresh cookie and local session state.
 */
import React, { createContext, useCallback, useContext, useMemo, useState, useEffect, ReactNode } from "react";
import { User } from "../types";
import { api } from "./api";
import { toast } from "sonner";
import { clearDocumentAssistantSession } from "@/lib/assistant/session";
import {
  AUTH_USER_KEY,
  clearAuthStorage,
  clearLegacyTokenStorage,
  setAccessToken,
} from "@/lib/auth-storage";
import { refreshAccessToken } from "@/lib/auth-tokens";
import { resolveApiUrl } from "@/lib/api-base-url";

const ACCESS_TOKEN_REFRESH_INTERVAL_MS = 25 * 60 * 1000;

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => void;
  rehydrate: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const rehydrate = useCallback(async () => {
    setLoading(true);
    clearLegacyTokenStorage();
    if (await refreshAccessToken()) {
      try {
        const verifiedUser = await api.get<User>("/api/auth/me");
        setUser(verifiedUser);
        localStorage.setItem(AUTH_USER_KEY, JSON.stringify(verifiedUser));
      } catch (error) {
        console.error("Session verification failed:", error);
        clearAuthStorage();
        setUser(null);
      }
    } else {
      clearAuthStorage();
      setUser(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    rehydrate();
  }, [rehydrate]);

  useEffect(() => {
    if (!user) return;

    const refreshSession = () => {
      refreshAccessToken().catch(() => {
        // Keep the current session until the next API call reports 401.
      });
    };

    const interval = window.setInterval(refreshSession, ACCESS_TOKEN_REFRESH_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [user]);

  const login = useCallback(async (email: string, pass: string) => {
    try {
      const response = await api.post<{ token: string; user: User }>(
        "/api/auth/login",
        { email, password: pass }
      );
      setAccessToken(response.token);
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(response.user));
      setUser(response.user);
      toast.success(`Welcome back, ${response.user.fullName}`);
    } catch (error: any) {
      console.error("Login Error:", error);
      toast.error(error.message || "Invalid email or password");
      throw error;
    }
  }, []);

  const logout = useCallback(() => {
    void fetch(resolveApiUrl("/api/auth/logout"), {
      method: "POST",
      credentials: "include",
    });
    clearAuthStorage();
    clearDocumentAssistantSession();
    setUser(null);
    toast.info("Logged out successfully");
  }, []);

  const value = useMemo<AuthContextType>(
    () => ({ user, loading, login, logout, rehydrate }),
    [loading, login, logout, rehydrate, user]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
