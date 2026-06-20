/**
 * Route guards for authenticated and role-restricted pages.
 *
 * ProtectedRoute — redirects to /login when no valid session.
 * RoleRoute      — redirects unauthorized roles to /error/403 (UI layer only;
 *                  backend must enforce the same rules).
 */
import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

export function RoleRoute({ children, allowedRoles }: { children: React.ReactNode, allowedRoles: string[] }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="flex items-center justify-center h-[50vh]">Loading...</div>;
  }

  if (!user || (user.role && !allowedRoles.includes(user.role.toLowerCase()))) {
    return <Navigate to="/error/403" replace />;
  }

  return <>{children}</>;
}
