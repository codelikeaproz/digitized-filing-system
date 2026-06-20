# DFS Developer Guide

Onboarding guide for the **Digitized Filing System (DFS)** — **DigiFile**, CMU’s institution-wide document management platform — a Django REST + React/Vite application for OrgUnit-scoped PDF document management.

> **Related docs:** [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [CHATBOT_CAPABILITIES.md](../CHATBOT_CAPABILITIES.md) · [DOCKER_SETUP.md](../DOCKER_SETUP.md) · [VESTA_DEPLOYMENT.md](./VESTA_DEPLOYMENT.md)

---

## 1. System overview

```text
React (Vite)  ──JWT──►  Django REST API  ──►  MySQL / SQLite
                              │
                              ├── MEDIA_ROOT (PDF files)
                              ├── SMTP (activation / reset emails)
                              └── OpenRouter (AI assistant, optional)
```

| Layer | Technology |
|-------|------------|
| Backend | Django 4.2, DRF, SimpleJWT |
| Frontend | React 18, Vite, TypeScript/TSX, shadcn/ui |
| Auth | JWT Bearer tokens (`Authorization: Bearer <token>`) |
| Roles | `admin`, `dept_head`, `staff` |

---

## 2. Repository layout

```text
project_dfs/
├── backend/                 # Django project root
│   ├── config/              # Settings, URLs, pagination, middleware
│   ├── accounts/            # Users, login, password flows
│   ├── documents/           # Folders, categories, documents, recycle bin
│   ├── orgunits/            # OrgUnit + OrgType hierarchy, storage allocation
│   ├── notifications/       # Storage threshold alerts + bell API
│   ├── auditlogs/           # Audit trail + exports
│   ├── backups/             # Admin database/media backup downloads
│   ├── employees/           # Requisitioners Directory (tagged-document references)
│   └── ai/                    # Document assistant chatbot
├── frontend/                # React SPA
│   └── src/
│       ├── pages/           # Route-level screens
│       ├── components/      # Reusable UI + feature components
│       ├── layouts/         # App shell
│       ├── lib/             # API client, auth, utilities
│       └── contexts/        # Shared React context (categories)
├── docs/                    # Developer + API documentation
├── backend/.env             # Django environment variables (never commit secrets)
└── frontend/.env            # Vite environment variables (never commit secrets)
```

### Why apps are organized this way

The backend uses **Django apps by domain**, not by HTTP layer. This matches Django conventions and avoids a risky migration:

| App | Responsibility |
|-----|----------------|
| `accounts` | Custom `User` model, JWT login, password reset/activation, user CRUD |
| `documents` | Folders, categories, PDF documents, upload, recycle bin, dashboard stats |
| `orgunits` | OrgUnit tree, OrgType lookup, hierarchical storage quotas |
| `notifications` | Storage threshold alerts, notification list/clear API |
| `auditlogs` | Immutable audit records, Excel export |
| `backups` | Admin-only database (`mysqldump`) and media ZIP downloads |
| `employees` | Requisitioners Directory CRUD (admin), read-only browse + scoped tagged counts (dept head) |
| `ai` | Document assistant (intent parsing + OpenRouter) |

**Recycle bin** and **dashboard** live inside `documents` because they operate on folder/document querysets — splitting them would duplicate scoping logic.

### First-time setup (Docker)

1. Copy `backend/.env.example` → `backend/.env` and `frontend/.env.example` → `frontend/.env`
2. Optional: set `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` in `backend/.env` for automatic admin creation on first startup
3. `docker compose -f docker-compose.dev.yml up --build`
4. Sign in at `http://localhost:5173` (auto-seeded admin or run `createsuperuser` manually if env vars are unset)

See [DOCKER_SETUP.md](../DOCKER_SETUP.md) for MySQL config, clean reset (`docker compose down -v`), and troubleshooting.

---

## 3. Access control model

Permissions are enforced **inline in views** (not a centralized DRF permission module). When adding endpoints, follow existing patterns.

### OrgUnit scoping

```python
# backend/documents/permissions.py — get_accessible_org_unit_ids(user)
admin      → no filter (global)
dept_head  → own org_unit + all descendant org_units
staff      → own org_unit only
no org_unit → empty queryset (non-admin)
```

Document list rejects out-of-scope `orgUnitId` / `folderId` with **403**.
OrgUnit list API (`GET /api/org-units/`) returns only accessible units for non-admins.

### Role capabilities (summary)

| Action | Admin | Dept Head | Staff |
|--------|-------|-----------|-------|
| View documents in scope | ✓ | ✓ | ✓ |
| Upload PDF | ✓ | ✓ | ✓ |
| Delete document | ✓ | ✓ | ✗ |
| Delete non-empty folder | ✓ | ✓ | ✗ |
| Delete empty folder | ✓ | ✓ | ✓ |
| Recycle bin | ✓ global | ✓ scoped | ✗ |
| Audit logs | ✓ global | ✓ scoped | ✗ |
| User management | ✓ all | ✓ staff in org subtree | ✗ |
| Requisitioners Directory | ✓ CRUD + global counts | ✓ read-only + scoped counts | ✗ (upload search API only) |
| OrgUnit / OrgType admin | ✓ (UI) | ✗ | ✗ |
| Backup downloads | ✓ | ✗ | ✗ |

### Where rules live

| Concern | File |
|---------|------|
| Folder/document write access | `documents/permissions.py` → `assert_folder_write_access`, `assert_document_write_access` |
| Recycle bin access | `documents/permissions.py` → `assert_recycle_bin_access` |
| User management | `accounts/views.py` → `UserViewSet._can_dept_head_manage` (subtree via `get_accessible_org_unit_ids`) |
| Audit log scope | `auditlogs/views.py` → `_scope_queryset` |
| Backup downloads | `backups/permissions.py` → `assert_backup_access` |
| Requisitioners Directory | `employees/permissions.py` → `assert_directory_read`, `assert_directory_admin` |
| OrgType admin-only | `orgunits/views.py` → `OrgTypeViewSet._require_admin` |
| Dashboard stats / storage rollup | `documents/dashboard_service.py` → `DashboardService` |
| Hierarchical storage quotas | `orgunits/storage.py` → allocation validation, usage rollup |
| Storage notifications | `notifications/storage_alerts.py`, `notifications/views.py` |

---

## 4. Backend development

### Run locally

```bash
cd backend
python manage.py runserver
```

See [DOCKER_SETUP.md](../DOCKER_SETUP.md) for container workflow.

### Live OpenAPI docs (Swagger UI)

After installing dependencies and restarting the backend:

| URL | Purpose |
|-----|---------|
| `http://localhost:8000/api/docs/` | Interactive Swagger UI |
| `http://localhost:8000/api/schema/` | OpenAPI schema (JSON) |

Requires `drf-spectacular` in `backend/requirements.txt`.

### Key files to read first

1. `config/urls.py` — all API mounts
2. `config/settings.py` — JWT, throttle, email, CORS
3. `documents/views.py` — largest API surface (upload, folders, recycle bin)
4. `accounts/views.py` — auth + users
5. `auditlogs/models.py` — `log_audit()` helper
6. `backups/services.py` — mysqldump + media ZIP generation

### Backup downloads (admin only)

- **UI:** `/backup` → Administration → Backup Management
- **API:** `GET /api/backups/database`, `GET /api/backups/media`
- **MySQL:** Backend Docker image includes `default-mysql-client` for `mysqldump`
- **SQLite dev:** Uses SQLite `.dump` when `DB_ENGINE=sqlite`
- **Temp files:** Written to `BACKUP_TEMP_DIR` (default `backend/tmp/backups`), deleted after download
- **Restore:** Manual / out of scope — import SQL into MySQL or replace `MEDIA_ROOT` contents yourself

### Adding a new API endpoint

1. Add serializer fields in `serializers.py`
2. Add view / viewset action in `views.py`
3. Register URL in app `urls.py`
4. Apply OrgUnit scoping in `get_queryset()` or assert helpers
5. Call `log_audit()` for user-visible mutations
6. Update `docs/API_DOCUMENTATION.md`

### Audit logging

```python
from auditlogs.models import log_audit

log_audit(
    request.user,
    "UPLOAD",                              # action code (uppercase)
    "Uploaded document: report.pdf",       # human-readable details
    target_type="Document",
    target_name="report.pdf",
    target_org_unit=folder.org_unit.name,
    ip_address=request.META.get("REMOTE_ADDR"),
)
```

### PDF upload pipeline

1. `POST /api/documents/upload` → `DocumentUploadView`
2. Require at least one of: PDF file (`file`) or `googleDriveLink` (or both)
3. `validate_pdf_upload()` — when `file` is present: extension, size (configurable via `SystemSettings.upload_limit_mb`, default 15 MB), `%PDF` header
4. `validate_global_storage_quota()` — blocks PDF uploads when system storage is full (skipped for Google Drive–only records)
5. `validate_storage_quota(org_unit)` — per–Office Unit cap (PDF uploads only)
6. Uploader enters a unique **document code** manually (`code` form field; validated in `document_code_validation.py`)
7. `Document.objects.create(...)` — metadata + optional PDF to `media/documents/YYYY/MM/DD/` and/or `google_drive_link`
8. `link_document_requisitioners()` (alias: `sync_requisitioners_to_directory()`) — directory tags link via `employeeId` FK and refresh snapshots from master; manual tags create a directory row only when no duplicate exists; document edits never mutate master `Employee` records
9. `add_storage_usage()` + threshold checks — file uploads only
10. `index_document_text(document)` — extract text for AI search when a PDF file is present

**Document codes:** Required on upload and edit. Pattern: letters, numbers, and hyphens only; stored uppercase; globally unique. See [DATA_MIGRATION_POLICY.md](./DATA_MIGRATION_POLICY.md).

**Requisitioners:** Upload/edit sends a `requisitioners` JSON array with `employeeId` + `source: "directory"` (read-only snapshots) or `source: "manual"` (editable; duplicate employee number or similar name blocked). Optional `employeeNumber` uses institutional format `Letter-Year-Code` (legacy numeric values allowed on document tags). Non-admin users search via `GET /api/employees?search=`; directory CRUD API remains admin-only. Directory employee number is locked when tagged on ≥1 document (admin override with reason + audit).

### Soft delete / recycle bin

- **Soft delete:** sets `is_deleted=True` on folder tree + documents
- **Restore:** `documents/services.py` → `restore_folder()`
- **Permanent delete:** removes DB rows + media files

### Hierarchical storage allocation

Office Unit storage uses a **parent envelope** model (`orgunits/storage.py`):

```text
System limit (Settings → System)
  └── Top-level Office Unit envelope (e.g. CISC 15 GB)
        ├── Child unit quota drawn from parent (e.g. SDO 5 GB)
        └── Parent pool available (e.g. 10 GB) for own files or future children
```

| Rule | Implementation |
|------|----------------|
| Top-level quota sum ≤ system limit | `get_top_level_allocated_quota_mb()`, `validate_org_unit_allocation_quota()` |
| Child sibling quotas ≤ parent envelope | `get_parent_available_allocation_mb()`, parent validation in serializer |
| Parent cannot shrink below child sum | `validate_parent_reduction()` |
| Display usage | `get_display_used_mb()` — subtree rollup for parents, own files for children |
| Dashboard subtree stats | `DashboardService.get_subtree_dashboard_stats()` — parent envelope quota, not sum of child quotas |

### Storage quota notifications

- **Global cap (physical):** `SystemSettings.storage_quota_mb` — compared against total document file sizes; drives upload blocking at 100% and physical-usage bell alerts at 80/90/95/100% (audience: `all`)
- **Top-level allocation pool:** sum of **root** Office Unit quotas cannot exceed system quota on create/update; child quotas validate against **parent envelope**, not the system pool directly
- **Per–Office Unit cap:** `OrgUnit.storage_quota_mb` — upload blocking when unit usage exceeds its quota; both global physical and per-unit checks must pass on upload
- **Allocation alerts:** 90% and 100% of top-level allocated quotas vs system limit (audience: `admin` only)
- **Service:** `notifications/storage_alerts.py` — `check_storage_thresholds()` (physical), `check_allocation_thresholds()` (allocated quotas), `validate_global_storage_quota()`
- **Hooks:** After upload, permanent delete, Office Unit quota changes, and when admin changes system quota
- **UI:** Notification bell in `AppShell` (`NotificationBell.tsx`) with unread count and **Clear** action (`POST /api/notifications/clear/`); admin configures limits under Settings → System; Office Units page shows **Envelope / To Children / Pool Available / Used / File Space Left** columns

---

## 5. Frontend development

### Run locally

```bash
cd frontend
npm install
npm run dev
```

Copy `frontend/.env.example` to `frontend/.env` and set `VITE_API_URL=http://localhost:8000`.

For backend setup, copy `backend/.env.example` to `backend/.env`. Do not use a shared root-level `.env` file.

### Key files

| File | Purpose |
|------|---------|
| `src/App.tsx` | Route table, lazy-loaded pages |
| `src/lib/api.ts` | Fetch wrapper, JWT header, upload helper |
| `src/lib/auth-context.tsx` | Login/logout, session rehydration |
| `src/components/ProtectedRoute.tsx` | Auth + role gates |
| `src/components/AppSidebar.tsx` | Role-based navigation |
| `src/pages/dashboard/DashboardPage.tsx` | Dashboard stats, storage charts, Office Unit filter |
| `src/pages/orgunits/OrgUnitsPage.tsx` | Office Unit CRUD, hierarchical quota modal + table |
| `src/components/notifications/NotificationBell.tsx` | Storage alert bell + clear |
| `src/lib/storage-quota-presets.ts` | Quota presets, allocation helpers, table formatters |
| `src/pages/employees/EmployeeDirectoryPage.tsx` | Requisitioners Directory (admin CRUD; dept head read-only) |
| `src/pages/documents/DocumentsPage.tsx` | Main document UI |

### API calls

```typescript
import { api } from "@/lib/api";

// JSON
const docs = await api.get<PaginatedResponse<Document>>("/api/documents", { page: 1 });

// Multipart upload
const formData = new FormData();
formData.append("file", pdfFile);
await api.upload("/api/documents/upload", formData);
```

Token is read from `localStorage.auth_token`. On `401`, client clears storage and redirects to `/login`.

### Route protection

- `ProtectedRoute` — requires login
- `RoleRoute` — requires one of `allowedRoles`; redirects unauthorized roles to `/error/403`

### Dashboard aggregation (by role)

| Viewer | Filter | Documents / storage scope |
|--------|--------|---------------------------|
| Admin | `office_unit=all` | Global — all units, system quota |
| Admin | Parent unit with children | Subtree — same as parent dept_head (`aggregates_subtree: true`) |
| Admin | Leaf unit | Single unit only |
| Parent dept_head | Default | Subtree of assigned unit |
| Child dept_head / staff | Default | Own unit only |

Implementation: `documents/dashboard_service.py`. See [API_DOCUMENTATION.md §7.2](./API_DOCUMENTATION.md#72-dashboard-api).

See [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) for the full route map.

---

## 6. Commenting standards

### Backend (Python)

- **Module docstring** at top of views, services, models — purpose, responsibilities, related frontend pages
- **Function docstring** on permission helpers, validation, and non-obvious business rules
- **Section comments** before each ViewSet class
- Do **not** comment obvious assignments

### Frontend (TSX)

- **File header block comment** on pages and major components
- **Inline comments** for role restrictions and non-obvious state/API flow
- Do **not** restate what JSX already shows

---

## 7. Testing checklist (manual)

After backend changes:

- [ ] Login as Admin, Dept Head, Staff
- [ ] List/upload document in scoped folder
- [ ] Staff cannot delete document
- [ ] Recycle bin restore + permanent delete
- [ ] User create + activation email flow
- [ ] Dashboard: admin parent-unit filter includes child documents; parent dept_head shows envelope quota (not parent + child sum)
- [ ] Office Units table: parent shows To Children + Pool Available; child shows "from {parent}"
- [ ] Notification clear removes visible alerts; badge count resets

After frontend changes:

- [ ] Protected routes redirect when logged out; role-restricted routes redirect to `/error/403`
- [ ] Upload dialog completes successfully

---

## 8. Known technical debt

Documented in [API_DOCUMENTATION.md §15](./API_DOCUMENTATION.md#15-known-limitations--needs-review):

- OrgUnit write endpoints enforce Admin-only on create/update (backend guard partial)
- AuditLog ViewSet exposes full ModelViewSet verbs
- No server-side logout / token denylist
- JWT refresh not wired in frontend

---

## 9. Maintenance workflow

| Change type | Update |
|-------------|--------|
| New/changed API route | `docs/API_DOCUMENTATION.md` + app `urls.py` header |
| New role rule | View assert helper + this guide §3 + frontend `RoleRoute` |
| New page | `App.tsx` + `FRONTEND_ROUTES.md` + sidebar if needed |
| Storage / dashboard change | `API_DOCUMENTATION.md` §7.2 + § Hierarchical storage + `DEVELOPER_GUIDE.md` §4 |
| Office Units UI / quota display | `ALPHA_TEST_CHECKLIST.md` §7 + `API_DOCUMENTATION.md` Office Units fields |
| Requisitioners Directory RBAC | `API_DOCUMENTATION.md` §7.16 + `employees/permissions.py` |
| User password on create/edit | `API_DOCUMENTATION.md` users API + `UsersPage.tsx` |
| Document upload / metadata change | `API_DOCUMENTATION.md` upload and edit endpoints + `DATA_MIGRATION_POLICY.md` |
| Chatbot behavior | `CHATBOT_CAPABILITIES.md` + `ai/services/intent_service.py` |

---

## 10. Suggested future structure (optional)

```text
backend/documents/
├── permissions.py  # OrgUnit + role checks (implemented)
├── services.py     # recycle bin folder tree operations
└── validators/     # optional: PDF/folder validation split
```

**Do not migrate** further until pain points justify the refactor cost.
