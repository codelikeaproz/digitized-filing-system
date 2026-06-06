# Frontend Routes

Route map for the DFS React SPA. Defined in `frontend/src/App.tsx`.

---

## Public routes (no authentication)

| Path | Component | Purpose |
|------|-----------|---------|
| `/login` | `LoginPage` | Email/password login → stores JWT |
| `/forgot-password` | `ForgotPasswordPage` | Request password reset email |
| `/reset-password/:uid/:token` | `ResetPasswordPage` | Complete password reset from email |
| `/set-password/:uid/:token` | `SetPasswordPage` | Activate new account + set password |
| `/error/429` | `Error429Page` | Rate limit exceeded (login throttle) |
| `/error/500` | `Error500Page` | Server error fallback |

---

## Protected routes (login required)

Wrapped by `ProtectedRoute` + `AppShell` layout.

| Path | Component | Role gate | Backend scope |
|------|-----------|-----------|---------------|
| `/` | `DashboardPage` | All roles | `GET /api/dashboard/stats` |
| `/documents` | `DocumentsPage` | All roles | Documents, folders, upload, AI assistant |
| `/settings` | `SettingsPage` | All roles | `POST /api/auth/update-password` |
| `/users` | `UsersPage` | `admin`, `dept_head` | ` /api/users` |
| `/audit-logs` | `AuditLogsPage` | `admin` only | `/api/audit-logs/` |
| `/org-units` | `OrgUnitsPage` | `admin` only | `/api/org-units/`, `/api/org-types/` |
| `/backup` | `BackupManagementPage` | `admin` only | `/api/backups/database`, `/api/backups/media` |
| `/recycle-bin` | `RecycleBinPage` | `admin`, `dept_head` | `/api/recycle-bin` |

> **Staff** see Dashboard, Documents, and Settings only (sidebar + route guards must stay in sync).

---

## Route guards

### `ProtectedRoute`

- Waits for auth rehydration (`GET /api/auth/me`)
- Redirects unauthenticated users to `/login` with `location` state

### `RoleRoute`

- Checks `user.role` against `allowedRoles`
- Shows "Access Denied" and redirects to `/` if role not allowed
- **Frontend-only** — backend must still enforce permissions

---

## Global wrappers

| Wrapper | Location | Behavior |
|---------|----------|----------|
| `AuthProvider` | `App.tsx` | Session state, login/logout |
| `CategoryProvider` | Inside protected layout | Shared category list for upload/forms |
| `AutoLogout` | `App.tsx` | Idle timeout (10 minutes) |
| `PublicAssistantMount` | `App.tsx` | Public onboarding chatbot (no document access) |
| `DocumentAssistant` | `DocumentsPage` | Logged-in document assistant drawer |

---

## Lazy loading

All page components are `React.lazy()` imported in `App.tsx` for code splitting. Add new pages the same way:

```tsx
const NewPage = lazy(() => import("./pages/new/NewPage"));
```

---

## Catch-all

| Path | Behavior |
|------|----------|
| `*` | Redirect to `/` |

---

## Sidebar alignment

Navigation items are role-filtered in `components/AppSidebar.tsx`. When adding a protected route:

1. Add route in `App.tsx` with correct `RoleRoute`
2. Add menu item to the appropriate role array in `AppSidebar.tsx`
3. Update this file and `DEVELOPER_GUIDE.md`
