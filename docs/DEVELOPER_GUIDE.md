# DFS Developer Guide

Onboarding guide for the **Digitized Filing System (DFS)** — a Django REST + React/Vite application for OrgUnit-scoped PDF document management.

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
│   ├── orgunits/            # OrgUnit + OrgType hierarchy
│   ├── auditlogs/           # Audit trail + exports
│   ├── backups/             # Admin database/media backup downloads
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
| `orgunits` | OrgUnit tree, OrgType lookup |
| `auditlogs` | Immutable audit records, Excel export |
| `backups` | Admin-only database (`mysqldump`) and media ZIP downloads |
| `ai` | Document assistant (intent parsing + OpenRouter) |

**Recycle bin** and **dashboard** live inside `documents` because they operate on folder/document querysets — splitting them would duplicate scoping logic.

### First-time setup (Docker)

1. Copy `backend/.env.example` → `backend/.env` and `frontend/.env.example` → `frontend/.env`
2. `docker compose up --build`
3. Create the admin login once: `docker compose exec backend python manage.py createsuperuser` (email = username, role auto-set to `admin`, Org Unit optional)

See [DOCKER_SETUP.md](../DOCKER_SETUP.md) for MySQL config, clean reset (`docker compose down -v`), and troubleshooting. Migrations do **not** seed a default user.

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
| OrgType admin-only | `orgunits/views.py` → `OrgTypeViewSet._require_admin` |

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
2. `validate_pdf_upload()` — extension, size (configurable via `SystemSettings.upload_limit_mb`, default 15 MB), `%PDF` header
3. `validate_global_storage_quota()` — blocks when system storage is full
4. `validate_storage_quota(org_unit)` — per–Office Unit cap
5. `generate_document_code(category)` — `{CategoryCode}-{Year}-{Sequence}` via `DocumentSequence` (locked per `category_code` + year)
6. `Document.objects.create(...)` — metadata + file to `media/documents/YYYY/MM/DD/`
7. `add_storage_usage()` + `check_storage_thresholds()` — updates usage and may create bell notifications
8. `index_document_text(document)` — extract text for AI search

**Document codes:** Preview with `GET /api/documents/next-code?categoryId=`. Assigned at upload. When a document's category is changed on edit, or when a category abbreviation changes in Manage Categories, auto-generated document codes swap their prefix only (e.g. `MEM-2026-000001` → `TES-2026-000001`); legacy non-standard codes are unchanged. Category codes are auto-generated from the category name on create/rename, or set manually via Manage Categories. Sequence counters are shared globally per category code and year.

### Soft delete / recycle bin

- **Soft delete:** sets `is_deleted=True` on folder tree + documents
- **Restore:** `documents/services.py` → `restore_folder()`
- **Permanent delete:** removes DB rows + media files

### Storage quota notifications

- **Global cap (physical):** `SystemSettings.storage_quota_mb` — compared against total document file sizes; drives upload blocking at 100% and physical-usage bell alerts at 80/90/95/100%
- **Allocation pool:** sum of `OrgUnit.storage_quota_mb` cannot exceed system quota on Office Unit create/update (`orgunits/storage.py` → `validate_org_unit_allocation_quota()`)
- **Per–Office Unit cap:** `OrgUnit.storage_quota_mb` — upload blocking when unit usage exceeds its quota; both global physical and per-unit checks must pass on upload
- **Service:** `notifications/storage_alerts.py` — `check_storage_thresholds()` (physical), `check_allocation_thresholds()` (allocated quotas), `validate_global_storage_quota()`
- **Hooks:** After upload, permanent delete, Office Unit quota changes, and when admin changes system quota
- **UI:** Notification bell in `AppShell`; admin configures limits under Settings → System; Office Units modal shows allocation headroom remaining

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
- `RoleRoute` — requires one of `allowedRoles` (mirrors sidebar, not a substitute for backend checks)

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

After frontend changes:

- [ ] Protected routes redirect when logged out
- [ ] Role-restricted pages show Access Denied
- [ ] Upload dialog completes successfully

---

## 8. Known technical debt

Documented in [API_DOCUMENTATION.md §15](./API_DOCUMENTATION.md#15-known-limitations--needs-review):

- Dashboard stats not role-scoped
- OrgUnit write endpoints enforce Admin-only on create/update
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
| Document upload / metadata change | `API_DOCUMENTATION.md` upload and edit endpoints |
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
