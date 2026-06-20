/**
 * Authentication context — session state for the SPA.
 *
 * On load: rehydrates user via GET /api/auth/me when auth_token exists.
 * Login:   POST /api/auth/login → stores access + refresh tokens and user.
 * Logout:  client-side only (clears tokens; no server revoke endpoint).
 */
import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { User } from "../types";
import { api } from "./api";
import { toast } from "sonner";
import { clearDocumentAssistantSession } from "@/lib/assistant/session";
import {
  AUTH_USER_KEY,
  clearAuthStorage,
  getAccessToken,
  setAuthTokens,
} from "@/lib/auth-storage";
import { refreshAccessToken } from "@/lib/auth-tokens";

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

  // Rehydrate auth state from localStorage
  const rehydrate = async () => {
    setLoading(true);
    const token = getAccessToken();
    const storedUser = localStorage.getItem(AUTH_USER_KEY);

    if (token && storedUser) {
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
      setUser(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    rehydrate();
  }, []);

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

  const login = async (email: string, pass: string) => {
    try {
      const response = await api.post<{ token: string; refresh: string; user: User }>(
        "/api/auth/login",
        { email, password: pass }
      );
      setAuthTokens(response.token, response.refresh);
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(response.user));
      setUser(response.user);
      toast.success(`Welcome back, ${response.user.fullName}`);
    } catch (error: any) {
      console.error("Login Error:", error);
      toast.error(error.message || "Invalid email or password");
      throw error;
    }
  };

  const logout = () => {
    clearAuthStorage();
    clearDocumentAssistantSession();
    setUser(null);
    toast.info("Logged out successfully");
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, rehydrate }}>
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
