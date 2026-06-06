/**
 * DFS Application Router
 *
 * Defines all client-side routes, lazy-loaded pages, and access guards.
 *
 * Public routes: login, password reset/activation, error pages
 * Protected shell: AppShell with sidebar (requires JWT)
 *
 * Role-restricted routes (must match AppSidebar menu):
 *   - /audit-logs, /org-units, /backup  → admin only
 *   - /users, /recycle-bin        → admin, dept_head
 *
 * Global providers: AuthProvider, CategoryProvider (inside shell), AutoLogout
 *
 * @see docs/FRONTEND_ROUTES.md
 */
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Suspense, lazy } from "react";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/lib/auth-context";
import { CategoryProvider } from "@/contexts/CategoryContext";
import { ProtectedRoute, RoleRoute } from "@/components/ProtectedRoute";

// Lazy load pages
const LoginPage = lazy(() => import("./pages/auth/LoginPage"));
const ForgotPasswordPage = lazy(() => import("./pages/auth/ForgotPasswordPage"));
const ResetPasswordPage = lazy(() => import("./pages/auth/ResetPasswordPage"));
const SetPasswordPage = lazy(() => import("./pages/auth/SetPasswordPage"));
const DashboardPage = lazy(() => import("./pages/dashboard/DashboardPage"));
const DocumentsPage = lazy(() => import("./pages/documents/DocumentsPage"));
const AuditLogsPage = lazy(() => import("./pages/auditlogs/AuditLogsPage"));
const SettingsPage = lazy(() => import("./pages/settings/SettingsPage"));
const UsersPage = lazy(() => import("./pages/users/UsersPage"));
const RecycleBinPage = lazy(() => import("./pages/recyclebin/RecycleBinPage"));
const OrgUnitsPage = lazy(() => import("./pages/orgunits/OrgUnitsPage"));
const BackupManagementPage = lazy(() => import("./pages/backup/BackupManagementPage"));
const Error429Page = lazy(() => import("./pages/errors/Error429Page"));
const Error500Page = lazy(() => import("./pages/errors/Error500Page"));

// Layout
import AppShell from "./layouts/AppShell";
import AutoLogout from "./components/AutoLogout";
import { PublicAssistantMount } from "@/components/assistant/public/PublicAssistantMount";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AutoLogout timeoutMinutes={10} />
        <Suspense fallback={<div className="flex items-center justify-center h-screen">Loading...</div>}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password/:uid/:token" element={<ResetPasswordPage />} />
            <Route path="/set-password/:uid/:token" element={<SetPasswordPage />} />
            <Route path="/error/429" element={<Error429Page />} />
            <Route path="/error/500" element={<Error500Page />} />
            <Route 
              path="/" 
              element={
                <ProtectedRoute>
                  <CategoryProvider>
                    <AppShell />
                  </CategoryProvider>
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="documents" element={<DocumentsPage />} />
              <Route path="audit-logs" element={
                <RoleRoute allowedRoles={['admin']}>
                  <AuditLogsPage />
                </RoleRoute>
              } />
              <Route path="users" element={
                <RoleRoute allowedRoles={['admin', 'dept_head']}>
                  <UsersPage />
                </RoleRoute>
              } />
              <Route path="org-units" element={
                <RoleRoute allowedRoles={['admin']}>
                  <OrgUnitsPage />
                </RoleRoute>
              } />
              <Route path="backup" element={
                <RoleRoute allowedRoles={['admin']}>
                  <BackupManagementPage />
                </RoleRoute>
              } />
              <Route path="recycle-bin" element={
                <RoleRoute allowedRoles={['admin', 'dept_head']}>
                  <RecycleBinPage />
                </RoleRoute>
              } />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
        <PublicAssistantMount />
        <Toaster />
      </BrowserRouter>
    </AuthProvider>
  );
}
