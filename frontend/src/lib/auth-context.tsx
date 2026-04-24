import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { User } from "../types";
import { api } from "./api";
import { toast } from "sonner";

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
    const token = localStorage.getItem("auth_token");
    const storedUser = localStorage.getItem("auth_user");

    if (token && storedUser) {
      try {
        // Verify token with backend
        const verifiedUser = await api.get<User>("/api/auth/me");
        setUser(verifiedUser);
        localStorage.setItem("auth_user", JSON.stringify(verifiedUser));
      } catch (error) {
        console.error("Session verification failed:", error);
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
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

  const login = async (email: string, pass: string) => {
    try {
      const response = await api.post<{ token: string; user: User }>("/api/auth/login", { email, password: pass });
      localStorage.setItem("auth_token", response.token);
      localStorage.setItem("auth_user", JSON.stringify(response.user));
      setUser(response.user);
      toast.success(`Welcome back, ${response.user.fullName}`);
    } catch (error: any) {
      console.error("Login Error:", error);
      toast.error(error.message || "Invalid email or password");
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
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
