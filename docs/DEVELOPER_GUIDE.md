# DFS Developer Guide

Onboarding guide for the **Digitized Filing System (DFS)** — a Django REST + React/Vite application for OrgUnit-scoped PDF document management.

> **Related docs:** [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) · [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md) · [CHATBOT_CAPABILITIES.md](../CHATBOT_CAPABILITIES.md) · [DOCKER_SETUP.md](../DOCKER_SETUP.md)

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
| `auditlogs` | Immutable audit records, CSV/XLSX export |
| `ai` | Document assistant (intent parsing + OpenRouter) |

**Recycle bin** and **dashboard** live inside `documents` because they operate on folder/document querysets — splitting them would duplicate scoping logic.

---

## 3. Access control model

Permissions are enforced **inline in views** (not a centralized DRF permission module). When adding endpoints, follow existing patterns.

### OrgUnit scoping

```python
# backend/documents/views.py — org_unit_scope_ids(user)
admin      → no filter (global)
dept_head  → own org_unit + all child org_units
staff      → own org_unit only
no org_unit → empty queryset (non-admin)
```

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
| User management | ✓ all | ✓ staff in org | ✗ |
| OrgUnit / OrgType admin | ✓ (UI) | ✗ | ✗ |

### Where rules live

| Concern | File |
|---------|------|
| Folder/document write access | `documents/permissions.py` → `assert_folder_write_access`, `assert_document_write_access` |
| Recycle bin access | `documents/permissions.py` → `assert_recycle_bin_access` |
| User management | `accounts/views.py` → `UserViewSet._enforce_manage_permission` |
| Audit log scope | `auditlogs/views.py` → `_scope_queryset` |
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
2. `validate_pdf_upload()` — extension, size (50MB), `%PDF` header
3. `Document.objects.create(...)` — metadata + file to `media/documents/YYYY/MM/DD/`
4. `index_document_text(document)` — extract text for AI search

### Soft delete / recycle bin

- **Soft delete:** sets `is_deleted=True` on folder tree + documents
- **Restore:** `documents/services.py` → `restore_folder()`
- **Permanent delete:** removes DB rows + media files

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
- OrgUnit write endpoints lack Admin-only backend guard
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
