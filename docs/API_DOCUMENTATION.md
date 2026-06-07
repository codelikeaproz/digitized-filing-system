# Digitized Filing System API Documentation

> **Generated from the current backend implementation.**  
> Source of truth: `backend/config/urls.py` and app-level `urls.py`, `views.py": "`, `serializers.py`, and `models.py`.

---

## 1. Overview

The **Digitized Filing System (DFS) API** is a Django REST Framework backend that powers a React + Vite frontend for managing PDF documents in an organization-scoped folder hierarchy.

| Topic | Implementation |
|--------|----------------|
| Framework | Django 4.2 + Django REST Framework |
| Authentication | JWT via `rest_framework_simplejwt` |
| Default permission | `IsAuthenticated` on all endpoints unless explicitly set to `AllowAny` |
| Roles | `admin`, `dept_head`, `staff` |
| Data scoping | OrgUnit-based; Department Heads include child OrgUnits |
| Documents | PDF-only uploads with metadata (code, requisitioners, description, keywords, category, folder) |
| Soft delete | Folders and documents use `is_deleted`; Recycle Bin supports restore and permanent delete |
| Audit logging | Server-side `log_audit()` helper; optional client-side audit POST from frontend |
| Time zone | `Asia/Manila` (formatted timestamps via `format_local_datetime`) |

### Architecture summary

```text
OrgUnit (hierarchy)
  └── Folder (parent/child subfolders)
        └── Document (PDF file + metadata)
Category (scoped per OrgUnit)
User (role + optional OrgUnit assignment)
```

---

## 2. Base URLs

| Environment | Base URL |
|-------------|----------|
| Local development | `http://localhost:8000` |
| Docker development | `http://localhost:8000` |
| Production | `https://your-production-domain.com` |

### URL prefix conventions

| Module | Prefix | Trailing slash |
|--------|--------|----------------|
| Accounts, Documents (most) | `/api/...` | **No** trailing slash on router resources (`trailing_slash=False`) |
| Org Units, Org Types, Audit Logs | `/api/...` | **Yes** trailing slash on router resources (DRF default) |
| AI Assistant | `/api/ai/...` | Mixed (see AI section) |
| Media files | `/media/...` | Served when `DEBUG=True` or via reverse proxy in production |

> **Frontend note:** The React app uses `VITE_API_URL` (default `http://localhost:8000`). Some frontend calls include a trailing slash while router paths may not — prefer the exact paths documented below.

---

## 3. Authentication

### 3.1 Login (application endpoint)

**Preferred by the React frontend.**

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/auth/login` or `/api/auth/login/` |
| **Auth** | None (`AllowAny`) |
| **Rate limit** | `5/minute` per IP (`LoginRateThrottle`) |

**Request body:**

```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

**Success `200`:**

```json
{
  "token": "<access_token>",
  "refresh": "<refresh_token>",
  "user": {
    "id": "1",
    "email": "user@example.com",
    "fullName": "Jane Doe",
    "role": "staff",
    "orgUnitId": "2",
    "orgUnitName": "CISC",
    "isActive": true,
    "createdAt": "2026-05-24 10:00:00",
    "isLastActiveAdmin": false,
    "hasUsablePassword": true,
    "activationStatus": "active",
    "activationEmailSentAt": null,
    "activationExpiresAt": null
  }
}
```

**Errors:**

| Status | Body | Cause |
|--------|------|-------|
| `400` | `{"error": "Invalid email or password."}` | Wrong credentials or inactive account |
| `429` | `{"error": "Too Many Requests", "message": "Too many login attempts. Please try again shortly."}` | Login throttle exceeded |

**Notes for frontend developers:**

- Store `token` in `localStorage` as `auth_token` (see `frontend/src/lib/api.ts`).
- Login requires both `is_active` and `is_active_status` to be true.
- New users created by Admin/Dept Head receive an activation email; they cannot log in until they call **Set Password**.

---

### 3.2 SimpleJWT token endpoints (alternate)

| | |
|---|---|
| **Obtain pair** | `POST /api/token/` |
| **Refresh** | `POST /api/token/refresh/` |

**Refresh request:**

```json
{
  "refresh": "<refresh_token>"
}
```

**Refresh success `200`:**

```json
{
  "access": "<new_access_token>"
}
```

| Setting | Value |
|---------|-------|
| Access token lifetime | 30 minutes |
| Refresh token lifetime | 1 day |

> The React app currently uses `/api/auth/login` (returns `token` + `refresh`), not `/api/token/`.

---

### 3.3 Get current user profile

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/auth/me` |
| **Auth** | Bearer JWT |

**Success `200`:** Same user object shape as login `user` field.

---

### 3.4 Update password (authenticated)

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/auth/update-password` or `/api/auth/update-password/` |
| **Auth** | Bearer JWT |

**Request body:**

```json
{
  "current_password": "OldPass123!",
  "new_password": "NewPass456!",
  "confirm_password": "NewPass456!"
}
```

**Success `200`:**

```json
{
  "message": "Password updated successfully. Please login again."
}
```

**Validation rules:**

- Current password must match
- New and confirm passwords must match
- New password must differ from current password
- Django password validators apply (minimum length, common password, numeric-only, similarity)

---

### 3.5 Forgot password

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/auth/forgot-password` or `/api/auth/forgot-password/` |
| **Auth** | None |

**Request body:**

```json
{
  "email": "user@example.com"
}
```

**Success `200` (always, to prevent email enumeration):**

```json
{
  "message": "If this email exists, a password reset link has been sent."
}
```

Reset links expire after **30 minutes** (`PASSWORD_RESET_TIMEOUT`).

---

### 3.6 Reset password (from email link)

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/auth/reset-password` or `/api/auth/reset-password/` |
| **Auth** | None |

**Request body:**

```json
{
  "uid": "<urlsafe_base64_user_id>",
  "token": "<django_token>",
  "new_password": "NewPass456!",
  "confirm_password": "NewPass456!"
}
```

**Success `200`:**

```json
{
  "message": "Password reset successful. Please login."
}
```

---

### 3.7 Set password / activate account (from activation email)

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/auth/set-password` or `/api/auth/set-password/` |
| **Auth** | None |

**Request body:**

```json
{
  "uid": "<urlsafe_base64_user_id>",
  "token": "<django_token>",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!"
}
```

**Success `200`:**

```json
{
  "message": "Account activated successfully. Please login."
}
```

Sets `is_active` and `is_active_status` to `true`.

---

### 3.8 Logout

**Status: Not implemented server-side.**

The frontend clears `auth_token` and `auth_user` from `localStorage` on logout. JWT tokens remain valid until expiry unless you add a denylist.

---

### 3.9 Authorization header

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

For file uploads, omit `Content-Type` so the browser sets the multipart boundary.

---

## 4. Roles and Access Rules

### Admin (`admin`)

- Global access to documents, folders, categories (all OrgUnits)
- Full user management (create, update, deactivate, delete)
- OrgUnit and OrgType management
- Recycle Bin: global view of deleted items
- Audit logs: full view and export
- Can delete documents and any folder (including non-empty)
- Dashboard stats: **global** for admin (`office_unit=all`); **subtree aggregated** when admin or parent dept_head views a parent unit with children; **single unit** for leaf filters; **own unit** for staff and child-only dept_head

### Department Head (`dept_head`)

- Document/folder access: own OrgUnit **and child OrgUnits**
- User management: **Staff only**, within assigned OrgUnit **subtree** (child dept_heads read-only)
- Cannot assign Admin or Dept Head roles
- Cannot move users outside their OrgUnit
- Recycle Bin: scoped to OrgUnit + children
- Audit logs: scoped to OrgUnit + children
- Can delete documents; can delete folders (Staff restrictions do not apply to Dept Head)

### Staff (`staff`)

- Document/folder access: own OrgUnit only
- Cannot manage users
- **Cannot delete documents**
- Can delete **empty** folders only (no documents, no subfolders)
- **No Recycle Bin access** (`403`)
- **No Audit Log access** (`403`)

### OrgUnit scoping helper

Centralized in `backend/documents/permissions.py`:

```python
# get_accessible_org_unit_ids(user) / org_unit_scope_ids(user)
# dept_head scope = [org_unit.id] + all descendant org unit ids
# staff scope = [org_unit.id]
# admin = no filter (callers skip queryset filters)
```

Out-of-scope `orgUnitId` or `folderId` query parameters on document list return **403** (defense in depth).

Users without an assigned OrgUnit see empty querysets for scoped resources (except Admin).

---

## 5. Common Response Format

The API does **not** use a single global envelope. Responses vary by endpoint:

### Success with message

```json
{
  "message": "Folder deleted successfully",
  "documents_deleted": 3
}
```

### Direct resource (ViewSet create/update)

```json
{
  "id": "12",
  "name": "Reports",
  "orgUnitId": "2"
}
```

### Validation error (`400`)

```json
{
  "message": "Organization unit is required for Dept Head and Staff.",
  "errors": {
    "orgUnitId": ["This field is required."]
  }
}
```

Or field-keyed DRF errors:

```json
{
  "name": ["Category name cannot be empty."]
}
```

### Permission error (`403`)

```json
{
  "detail": "You do not have permission to perform this action."
}
```

Or custom:

```json
{
  "message": "Staff users cannot manage user accounts."
}
```

### Generic error

```json
{
  "error": "Valid category is required."
}
```

---

## 6. Common Status Codes

| Status Code | Meaning | Typical Cause |
|-------------|---------|---------------|
| `200` | OK | Successful GET, PATCH, or action |
| `201` | Created | Resource created (user, document upload, folder) |
| `204` | No Content | User hard-deleted |
| `400` | Bad Request | Validation error, business rule violation |
| `401` | Unauthorized | Missing or expired JWT |
| `403` | Forbidden | Role or OrgUnit restriction |
| `404` | Not Found | Resource not found or not visible in scope |
| `405` | Method Not Allowed | Public registration disabled |
| `409` | Conflict | Duplicate document code |
| `415` | Unsupported Media Type | Non-PDF upload (implicit via validation) |
| `429` | Too Many Requests | Login or activation email throttle |
| `500` | Server Error | Unexpected backend failure |

---

## 7. Endpoint Groups

### 7.1 Authentication API

| Endpoint | Method | Path | Auth | Notes |
|----------|--------|------|------|-------|
| Login | POST | `/api/auth/login` | No | Primary login; rate-limited |
| Current user | GET | `/api/auth/me` | Yes | Profile for session rehydration |
| Update password | POST | `/api/auth/update-password` | Yes | Changes password for logged-in user |
| Forgot password | POST | `/api/auth/forgot-password` | No | Sends reset email if account exists |
| Reset password | POST | `/api/auth/reset-password` | No | Completes email reset flow |
| Set password / activate | POST | `/api/auth/set-password` | No | First-time account activation |
| JWT obtain pair | POST | `/api/token/` | No | Alternate SimpleJWT login |
| JWT refresh | POST | `/api/token/refresh/` | No | Refresh access token |
| Public register | POST | `/api/user/register` | No | **Disabled** — returns `405` |
| Logout | — | — | — | **Not implemented** (client-side only) |

---

### 7.2 Dashboard API

#### Get dashboard statistics

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/dashboard/` (preferred) or `/api/dashboard/stats` (legacy alias) |
| **Auth** | Bearer JWT |
| **Roles** | All authenticated users |

**Query parameters:**

| Parameter | Values | Access |
|-----------|--------|--------|
| `office_unit` | `all` (default for admin), Office Unit ID | Admin: any unit. Dept Head: own unit or descendant IDs only. Staff: ignored (own unit only). |

**Role behavior:**
- **Admin** — `office_unit=all` returns global stats + storage comparison chart data; filtering to a **parent unit with children** aggregates documents and usage across the subtree (same as parent dept_head), uses the parent's quota envelope (not the sum of child quotas), and includes `storage_by_office_unit` breakdown; filtering to a **leaf unit** returns single-unit stats only
- **Dept Head (parent unit)** — default view aggregates own unit + all descendants; `storage.quota_mb` is the parent allocation envelope; `storage_by_office_unit` lists each accessible child; `can_filter_office_units` is true when descendants exist; `aggregates_subtree` is true
- **Dept Head (child-only or filtered to child)** — scoped to selected unit; comparison chart still lists accessible subtree units when applicable; `aggregates_subtree` is false
- **Staff** — always scoped to assigned Office Unit; filter param ignored

**Response fields:**

| Field | Description |
|-------|-------------|
| `aggregates_subtree` | `true` when document counts and file usage include descendant Office Units |
| `can_filter_office_units` | Whether the client may show an Office Unit filter dropdown |
| `storage.org_units_quota_mb` | Global view only: sum of top-level unit quotas |
| `storage.org_units_allocation_remaining_mb` | Global view only: system pool not yet assigned to top-level units |
| `storage.children_allocated_mb` | Subtree view only: sum of direct child quotas under the selected parent |
| `storage.available_for_allocation_mb` | Subtree view only: parent envelope minus `children_allocated_mb` |
| `storage_by_office_unit[]` | Comparison chart rows: `org_unit_id`, `org_unit_name`, `quota_mb`, `used_mb`, `remaining_mb`, `usage_percentage` |

**Success `200` (global):**

```json
{
  "scope": "global",
  "office_unit_name": "All Office Units",
  "office_unit_filter": "all",
  "can_filter_office_units": true,
  "aggregates_subtree": false,
  "total_documents": 42,
  "uploaded_files": 42,
  "total_org_units": 5,
  "total_users": 18,
  "deleted_files": null,
  "storage": {
    "org_unit_name": "All Office Units",
    "quota_mb": 15360,
    "org_units_quota_mb": 15360,
    "org_units_allocation_remaining_mb": 0,
    "used_mb": 9.68,
    "remaining_mb": 15350.32,
    "usage_percentage": 0.1,
    "percent_used": 0.1
  },
  "storage_by_office_unit": [
    {
      "org_unit_id": "1",
      "org_unit_name": "CISC",
      "quota_mb": 15360,
      "used_mb": 9.68,
      "remaining_mb": 15350.32,
      "usage_percentage": 0.1
    },
    {
      "org_unit_id": "2",
      "org_unit_name": "SDO",
      "quota_mb": 5120,
      "used_mb": 9.68,
      "remaining_mb": 5110.32,
      "usage_percentage": 0.2
    }
  ]
}
```

**Success `200` (leaf Office Unit — single unit, no descendants):**

```json
{
  "scope": "office_unit",
  "office_unit_id": "2",
  "office_unit_name": "SDO",
  "office_unit_filter": "2",
  "can_filter_office_units": false,
  "aggregates_subtree": false,
  "total_documents": 2,
  "uploaded_files": 2,
  "total_org_units": null,
  "total_users": 1,
  "deleted_files": 0,
  "storage": {
    "org_unit_id": "2",
    "org_unit_name": "SDO",
    "quota_mb": 5120,
    "used_mb": 9.68,
    "remaining_mb": 5110.32,
    "usage_percentage": 0.2,
    "percent_used": 0.2
  },
  "storage_by_office_unit": []
}
```

**Success `200` (parent Office Unit with children — admin filter or parent dept_head default):**

When the selected unit has active child Office Units, document counts and file usage aggregate across the subtree. `storage.quota_mb` is the **parent envelope** (not the sum of parent + child quotas).

```json
{
  "scope": "office_unit",
  "office_unit_id": "1",
  "office_unit_name": "CISC",
  "office_unit_filter": "1",
  "can_filter_office_units": true,
  "aggregates_subtree": true,
  "total_documents": 2,
  "uploaded_files": 2,
  "total_org_units": 2,
  "total_users": 2,
  "deleted_files": 0,
  "storage": {
    "org_unit_id": "1",
    "org_unit_name": "CISC",
    "quota_mb": 15360,
    "used_mb": 9.68,
    "remaining_mb": 15350.32,
    "usage_percentage": 0.1,
    "percent_used": 0.1,
    "children_allocated_mb": 5120,
    "available_for_allocation_mb": 10240
  },
  "storage_by_office_unit": [
    {
      "org_unit_id": "1",
      "org_unit_name": "CISC",
      "quota_mb": 15360,
      "used_mb": 9.68,
      "remaining_mb": 15350.32,
      "usage_percentage": 0.1
    },
    {
      "org_unit_id": "2",
      "org_unit_name": "SDO",
      "quota_mb": 5120,
      "used_mb": 9.68,
      "remaining_mb": 5110.32,
      "usage_percentage": 0.2
    }
  ]
}
```

**Storage calculations (global admin view):**

- `storage.quota_mb` — system-wide cap from Settings → System (`SystemSettings.storage_quota_mb`); drives utilization percentage, notifications, and upload blocking
- `storage.org_units_quota_mb` — sum of **top-level** (root) Office Unit `storage_quota_mb` values only; child quotas are drawn from their parent envelope and are **not** added here
- `storage.org_units_allocation_remaining_mb` — unassigned top-level pool: `storage.quota_mb - org_units_quota_mb`
- `storage.used_mb`, `storage.remaining_mb`, `storage.usage_percentage` — computed from sum of all `Document.file_size` vs system `quota_mb` (file usage, not allocation)
- `storage_by_office_unit` — per-unit breakdown; parent rows use subtree file rollup in `used_mb`

**Storage calculations (Office Unit scope):**

| Field | Leaf unit | Parent with children (`aggregates_subtree: true`) |
|-------|-----------|---------------------------------------------------|
| `storage.quota_mb` | Unit's own quota | Parent **envelope** only (e.g. 15 GB, not 15 + 5 GB) |
| `storage.used_mb` | Own folder file sizes | Subtree rollup (own + all descendants) |
| `storage.remaining_mb` | `quota_mb - used_mb` (file space left) | Same, based on parent envelope |
| `storage.children_allocated_mb` | — | Sum of direct children's quotas |
| `storage.available_for_allocation_mb` | — | `quota_mb - children_allocated_mb` (pool still assignable to children) |

**Display note:** When file usage is tiny relative to system quota (e.g. 9.68 MB vs 15 GB), `usage_percentage` may round to `0.0` or `0.1`. The frontend shows `< 0.1%` when usage is non-zero but below one decimal place.

---

### Hierarchical storage allocation

Office Unit storage follows the org hierarchy:

- **Top-level units** (`parentId` null): quota validated against remaining **system** storage (`sum(top-level quotas) <= system quota`).
- **Child units**: quota validated against remaining **parent** allocation (`sum(direct sibling quotas) <= parent.storage_quota_mb`).
- **Multi-level**: each child validates against its immediate parent only (e.g. Section under Department under College).
- **Parent reduction**: a parent quota cannot be set below the sum of its direct children's quotas.
- **Usage display**: parent units roll up own + descendant file usage; child units show own documents only.

**Response fields (list/create/update):**

| Field | Description |
|-------|-------------|
| `parentName` | Parent Office Unit name, or `null` for top-level |
| `storageUsedMb` | Own document usage (stored field) |
| `storageUsedDisplayMb` | Display usage (rollup for parents, own for children) |
| `storageOwnUsedMb` | File usage in this unit's folders only (excludes descendant units) |
| `storageRemainingMb` | File space left: `storageQuotaMb - storageUsedDisplayMb` |
| `childrenAllocatedMb` | Sum of direct children's quotas; `0` for leaf units (**To Children** column) |
| `availableForAllocationMb` | Pool remaining within envelope: `storageQuotaMb - childrenAllocatedMb`; always returned—for leaf units equals full envelope (**Pool Available** column) |
| `allocationContext` | `{ source, parentName, parentAllocationMb, childrenAllocatedMb, availableForAllocationMb }` where `source` is `system` or `parent` |

**Office Units table semantics (UI):**

- **Envelope** — total allocation for the unit (parent envelope includes all descendants; child envelope is drawn from parent)
- **To Children** — direct child quota sum; leaf units show **0 MB**
- **Pool Available** — envelope minus allocated children; for leaf units equals full envelope
- **Used (files)** — uploaded document bytes; parents show subtree rollup with own usage as secondary
- **File Space Left** — envelope minus file usage (not the same as Pool Available)

**Allocation error examples `400`:**

Top-level (system pool exhausted):

```json
{
  "storageQuotaMb": ["Insufficient available system storage.\n\nRequested: 500 MB\nAvailable: 200 MB\n\n..."],
  "message": "Insufficient available system storage."
}
```

Child exceeds parent pool:

```json
{
  "storageQuotaMb": ["Child Office Unit allocations exceed the available Parent Office Unit storage.\n\nParent Allocation: 15360 MB\nAllocated to Children: 18000 MB\nAvailable: 0 MB\n\n..."],
  "message": "Child Office Unit allocations exceed the available Parent Office Unit storage."
}
```

Parent reduction blocked:

```json
{
  "storageQuotaMb": ["Parent allocation cannot be reduced below the total allocated child storage.\n\nCurrent Child Allocation: 12000 MB\nRequested Parent Allocation: 10240 MB"],
  "message": "Parent allocation cannot be reduced below the total allocated child storage."
}
```

---

### 7.3 Documents API

#### List documents

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/documents` |
| **Auth** | Bearer JWT |
| **Pagination** | Yes (`page`, `page_size`) |

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `folderId` | integer | Filter by folder |
| `orgUnitId` | integer | Filter by OrgUnit |
| `includeChildOrgUnits` | boolean | Default `true`; include child OrgUnits when filtering by `orgUnitId` |
| `category` | integer | Category ID |
| `search` | string | Matches title, code, description, requestor (legacy), requisitioner employee number/full name, keywords |
| `page` | integer | Page number |
| `page_size` | integer | Items per page (max 100) |

**Success `200`:**

```json
{
  "count": 25,
  "next": "http://localhost:8000/api/documents?page=2",
  "previous": null,
  "results": [
    {
      "id": "10",
      "title": "report.pdf",
      "file_name": "report.pdf",
      "filePath": "SDD > Reports",
      "file_url": "http://localhost:8000/media/documents/2026/05/24/report.pdf",
      "folderId": "3",
      "categoryId": "1",
      "category": "Reports",
      "code": "01-12551",
      "requestor": "202400123 - Jane Doe",
      "requisitioners": [
        {
          "employeeNumber": "202400123",
          "firstName": "Jane",
          "lastName": "Doe",
          "suffix": "",
          "fullName": "Jane Doe"
        }
      ],
      "description": "Monthly report",
      "keywords": ["report", "may"],
      "filingYear": 2026,
      "status": "Received",
      "source": "Uploaded",
      "mimeType": "application/pdf",
      "file_size": 204800,
      "createdAt": "2026-05-24 14:30:00"
    }
  ]
}
```

---

#### Retrieve document

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/documents/{id}` |
| **Auth** | Bearer JWT |
| **Scope** | OrgUnit-scoped queryset |

---

#### Upload PDF document

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/documents/upload` |
| **Auth** | Bearer JWT |
| **Content-Type** | `multipart/form-data` |

**Form fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `file` | Yes | PDF file |
| `folderId` | Yes | Target folder ID |
| `categoryId` | Yes | Category ID (must match folder OrgUnit if category is scoped; category must have a `code`) |
| `title` | No | Defaults to uploaded filename |
| `requisitioners` | Yes | JSON array string, e.g. `[{"employeeNumber":"202400123","firstName":"Jane","lastName":"Doe","suffix":""}]` (at least one; first/last name required; `employeeNumber` optional — digits only when provided; no duplicate non-empty employee numbers per document) |
| `requestor` | No | Legacy derived display string (synced server-side from `requisitioners`; do not send on manual upload) |
| `description` | Yes | Required; max 50 characters |
| `keywords` | No | JSON array string, e.g. `["keyword1","keyword2"]` |
| `filePath` | No | Display path; defaults to folder full path |
| `source` | No | `Uploaded` (default; legacy rows may show `Scanned`) |

**Success `201`:** Full `DocumentSerializer` object.

**Errors:**

| Status | Example |
|--------|---------|
| `400` | `{"error": "Only PDF files are supported."}` |
| `400` | `{"file": "File exceeds the maximum allowed size of 15 MB. Please compress the file and try again."}` |
| `400` | `{"file": "Storage quota exceeded. Please contact your system administrator."}` |
| `400` | `{"message": "Document Code is already used."}` |
| `409` | `{"message": "Document Code is already used."}` |

**PDF validation rules:**

- Extension must be `.pdf`
- File header must start with `%PDF`
- Max size: **Configurable** via System Settings (`upload_limit_mb`, default **15 MB**)
- File must not be empty

**Notes:** Document `code` is auto-generated server-side as `{CategoryCode}-{Year}-{Sequence}` (e.g. `RPT-2026-000001`). Do not send `code` in the upload form. After upload, PDF text is indexed via `index_document_text()` for AI search.

---

#### Preview next document code

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/documents/next-code` |
| **Auth** | Bearer JWT |

**Query parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `categoryId` | Yes | Category ID with a configured `code` (must be visible in the caller's Office Unit scope) |

**Success `200`:**

```json
{ "code": "RPT-2026-000155" }
```

Preview only — the final code is assigned atomically when upload completes.

---

#### Update document metadata

| | |
|---|---|
| **Method** | `PUT` / `PATCH` |
| **Path** | `/api/documents/{id}` |
| **Auth** | Bearer JWT |
| **Scope** | Must be in accessible OrgUnit |

Uses `DocumentSerializer` — document `code` is read-only in the serializer; prefix may update when category assignment changes via edit (see Edit document details).

---

#### Edit document details

| | |
|---|---|
| **Method** | `PATCH` |
| **Path** | `/api/documents/{id}/edit` |
| **Auth** | Bearer JWT |
| **Roles** | Admin, Dept Head |

**Request body (JSON):**

```json
{
  "folderId": "3",
  "categoryId": "1",
  "requisitioners": [
    { "employeeNumber": "202400123", "firstName": "Jane", "lastName": "Doe", "suffix": "" },
    { "employeeNumber": "202400456", "firstName": "Maria", "lastName": "Santos", "suffix": "" }
  ],
  "description": "Monthly report",
  "keywords": ["report", "may"],
  "file_name": "report"
}
```

- Replaces the full requisitioner list (add/update/remove sync)
- Document `code` is not sent in the body; when `categoryId` changes, auto-generated codes swap prefix only (`MEM-2026-000001` → `REP-2026-000001`). Legacy codes are unchanged.
- `requestor` in responses is derived as `"emp - name, emp - name"` for backward compatibility
- At least one requisitioner required; `employeeNumber` is optional (leave blank for non-employees). When provided, employee numbers must be digits only and unique per document among non-empty values

**Success `200`:** Full `DocumentSerializer` object.

---

#### Rename document file

| | |
|---|---|
| **Method** | `PATCH` |
| **Path** | `/api/documents/{id}/rename` |
| **Auth** | Bearer JWT |

**Request body:**

```json
{
  "file_name": "new-name.pdf"
}
```

- Extension is forced to `.pdf`
- Renames storage file and updates `title`
- Duplicate names in same folder rejected

---

#### Download document

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/documents/{id}/download/` |
| **Auth** | Bearer JWT |
| **Response** | PDF file stream (`Content-Disposition: attachment`) |

---

#### Soft-delete document

| | |
|---|---|
| **Method** | `DELETE` |
| **Path** | `/api/documents/{id}` |
| **Auth** | Bearer JWT |
| **Roles** | Admin, Dept Head — **Staff blocked** (`403`) |

Sets `is_deleted=true`; item appears in Recycle Bin.

---

#### View PDF in browser

Use `file_url` from document response (`/media/documents/YYYY/MM/DD/filename.pdf`).

---

### 7.4 Folders API

#### List folders

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/folders` |
| **Auth** | Bearer JWT |
| **Scope** | OrgUnit-scoped (Admin: all) |

---

#### Create folder / subfolder

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/folders` |
| **Auth** | Bearer JWT |

**Request body:**

```json
{
  "name": "Reports",
  "parentId": "5",
  "orgUnitId": "2"
}
```

| Field | Notes |
|-------|-------|
| `parentId` | Omit or `null` for root folder within OrgUnit |
| `orgUnitId` | Required when no parent; inherited from parent when `parentId` set |

**Validation:**

- Name cannot be empty
- Reserved names blocked: `all files`, `root`, `trash`, `recycle bin`
- Invalid characters: `\ / : * ? " < > \|`

---

#### Retrieve / update folder

| | |
|---|---|
| **GET** | `/api/folders/{id}` |
| **PUT/PATCH** | `/api/folders/{id}` |

---

#### Rename folder

| | |
|---|---|
| **Method** | `PATCH` |
| **Path** | `/api/folders/{id}/rename` |

**Request body:**

```json
{
  "name": "New Folder Name"
}
```

---

#### Delete folder (soft delete)

| | |
|---|---|
| **Method** | `DELETE` |
| **Path** | `/api/folders/{id}` |
| **Auth** | Bearer JWT |

**Behavior:**

- Soft-deletes folder, all subfolders, and contained documents
- **Staff:** can only delete **empty** folders (`403` if non-empty)
- Admin / Dept Head: can delete non-empty folders

**Success `200`:**

```json
{
  "message": "Folder deleted successfully",
  "documents_deleted": 4
}
```

---

#### Get folder tree

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/folders/tree` |
| **Auth** | Bearer JWT |

**Admin response:** Virtual `All Files` node + full OrgUnit hierarchy with nested folders.

**Dept Head response:** Virtual `All Files` node + OrgUnit subtree rooted at the assigned unit (includes descendant units and their folders).

**Staff response:** Virtual `All Files` node + single assigned OrgUnit node with folders (or flat folder list when unassigned).

**Example org-unit node:**

```json
{
  "id": "3",
  "name": "Reports",
  "type": "folder",
  "parentId": null,
  "orgUnitId": "2",
  "location": "Reports",
  "documentCount": 5,
  "subfolderCount": 1,
  "children": []
}
```

---

### 7.5 Categories API

#### List categories

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/categories` |
| **Auth** | Bearer JWT |
| **Scope** | OrgUnit-scoped for non-admin. Dept Head: own unit + descendant units (subtree). Staff: own unit only. |

**Query parameters:**

| Parameter | Description |
|-----------|-------------|
| `orgUnitId` | Filter by OrgUnit (must be within caller's scope for non-admin; 403 if tampered) |

**Response fields include:** `code`, `documentCount`, `inUse` (true if active documents exist).

---

#### Create category

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/categories` |

**Request body:**

```json
{
  "name": "Reports",
  "orgUnitId": "2"
}
```

- `code` — auto-generated from the category name when omitted (first 3 alphanumeric characters, deduped per Office Unit). Optional on create: send `"code": "AUD"` to set manually.
- Unique `(name, org_unit)` per category name; unique `(code, org_unit)` when code is non-empty
- **Dept Head** may create categories for any accessible Office Unit in their subtree (`orgUnitId` in scope)
- **Staff** may create categories for their assigned Office Unit only

---

#### Update category

| | |
|---|---|
| **Method** | `PUT` / `PATCH` |
| **Path** | `/api/categories/{id}` |

**Body:** `{ "name": "Updated Name", "code": "AUD" }` — `code` is optional.

- When `code` is sent, it is normalized (uppercase A–Z, 0–9, max 10) and saved as a **manual abbreviation override**.
- When `code` is omitted and the name changes, the server regenerates `code` from the new name (deduped within the Office Unit).
- When the category abbreviation changes, active documents in that category with auto-generated codes (`PREFIX-YEAR-SEQ`) have their prefix updated; sequence numbers are preserved (e.g. `MEM-2026-000001` → `TES-2026-000001`).
- **Dept Head** may update categories in their accessible subtree; **Staff** own unit only.

---

#### Delete category

| | |
|---|---|
| **Method** | `DELETE` |
| **Path** | `/api/categories/{id}` |

**Blocked when:**

- Active documents reference the category
- Caller lacks scope to the category's Office Unit (non-admin)

**Success `200`:**

```json
{
  "message": "Category deleted successfully"
}
```

---

### 7.6 Organization Units API

#### List OrgUnits

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/org-units/` |
| **Auth** | Bearer JWT |
| **Pagination** | Yes |

**Query parameters:**

| Parameter | Description |
|-----------|-------------|
| `search` | Matches name, type, org type name |
| `page`, `page_size` | Pagination |

**Response includes:** `userCount`, `folderCount`, `documentCount`, `childCount`, `canDelete`, `deleteBlockReason`, `parentName`, `storageUsedDisplayMb`, `storageOwnUsedMb`, `storageRemainingMb`, `childrenAllocatedMb`, `availableForAllocationMb`, `allocationContext`.

---

#### Create OrgUnit

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/org-units/` |

**Request body:**

```json
{
  "name": "Software Development Department",
  "parentId": "1",
  "org_type_id": 2,
  "storageQuotaMb": 1024
}
```

**Validation:**

- Name required; unique among siblings
- No circular parent relationships
- Active Org Type required (`org_type_id`)
- `storageQuotaMb` — admin only; minimum 1 MB
- **Top-level allocation:** cannot exceed system-wide `storage_quota_mb`; sum of top-level quotas must not exceed system quota
- **Child allocation:** sum of direct sibling quotas (including requested) must not exceed parent `storageQuotaMb`
- **Parent reduction:** parent quota cannot be set below sum of direct child quotas
- Quota cannot be set below the unit's own current file usage

**Allocation error `400`:** See [Hierarchical storage allocation](#hierarchical-storage-allocation) for message formats.

**Audit actions:** `CREATE_ORG_UNIT`, `UPDATE_ORG_UNIT`, `STORAGE_ALLOCATION_UPDATED` (quota change; distinguishes parent vs child allocation), `STORAGE_ALLOCATION_VALIDATION_FAILED` (includes parent context when applicable)

**Permissions:** Admin only (`403` for non-admin create/update).

---

#### Update OrgUnit

| | |
|---|---|
| **Method** | `PUT` / `PATCH` |
| **Path** | `/api/org-units/{id}/` |

Same hierarchical storage allocation validation as create. When updating quota, the unit's previous allocation is excluded from the sibling/top-level sum before checking headroom.

---

#### Delete OrgUnit (soft delete)

| | |
|---|---|
| **Method** | `DELETE` |
| **Path** | `/api/org-units/{id}/` |

**Blocked when OrgUnit has:** users, folders, documents, or child OrgUnits.

**Success `200`:**

```json
{
  "message": "Office Unit deleted successfully"
}
```

Sets `is_deleted=true` (not hard delete).

---

### 7.7 Org Types API

Database-driven org types used when creating/editing OrgUnits.

#### List OrgTypes

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/org-types/` |
| **Auth** | Bearer JWT |

**Query parameters:**

| Parameter | Description |
|-----------|-------------|
| `includeInactive` | `true` to include inactive types (Admin management UI) |

Default list returns **active only**.

---

#### Create OrgType

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/org-types/` |
| **Roles** | **Admin only** |

**Request body:**

```json
{
  "name": "Office",
  "is_active": true
}
```

`code` and `sort_order` are auto-generated.

---

#### Update OrgType

| | |
|---|---|
| **Method** | `PUT` / `PATCH` |
| **Path** | `/api/org-types/{id}/` |
| **Roles** | **Admin only** |

Use `is_active: false` to disable instead of deleting when in use.

---

#### Delete OrgType

| | |
|---|---|
| **Method** | `DELETE` |
| **Path** | `/api/org-types/{id}/` |
| **Roles** | **Admin only** |

Blocked if OrgUnits reference the type.

---

### 7.8 Users API

#### List users

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/users` |
| **Auth** | Bearer JWT |
| **Roles** | Admin (all users), Dept Head (own OrgUnit only) |
| **Pagination** | Yes |

**Query parameters:**

| Parameter | Description |
|-----------|-------------|
| `search` | Email, first name, last name |
| `role` | `admin`, `dept_head`, `staff` |
| `orgUnitId` | Filter by OrgUnit |
| `page`, `page_size` | Pagination |

Staff receive empty list (`403` not raised — empty queryset).

---

#### Create user

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/users` |
| **Roles** | Admin, Dept Head (Staff only, forced OrgUnit) |

**Request body:**

```json
{
  "email": "newuser@example.com",
  "fullName": "New User",
  "role": "staff",
  "orgUnitId": "2"
}
```

**Behavior:**

- User created **inactive** with unusable password
- Activation email sent automatically
- Admin: `orgUnitId` cleared when `role=admin`
- Dept Head: `role` forced to `staff`, `orgUnitId` forced to actor's OrgUnit

**Success `201`:** User object.

---

#### Update user

| | |
|---|---|
| **Method** | `PUT` / `PATCH` |
| **Path** | `/api/users/{id}` |

**Rules:**

- Dept Head can only update Staff in same OrgUnit
- Cannot demote/deactivate last active Admin
- Cannot deactivate own account

---

#### Activate / deactivate user

| Method | Path |
|--------|------|
| PATCH | `/api/users/{id}/status` — body: `{"isActive": true}` |
| PATCH | `/api/users/{id}/activate` |
| PATCH | `/api/users/{id}/deactivate` |

Activation requires user to have set password via activation link.

---

#### Resend activation email

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/users/{id}/resend-activation` |
| **Rate limit** | `3/hour` per user per IP |

---

#### Delete user (hard delete)

| | |
|---|---|
| **Method** | `DELETE` |
| **Path** | `/api/users/{id}` |
| **Roles** | **Admin only** |

Cannot delete self or last active Admin.

**Success `204`:** No content.

---

### 7.9 Audit Logs API

#### List audit logs

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/audit-logs/` |
| **Auth** | Bearer JWT |
| **Roles** | Admin (all), Dept Head (scoped) — **Staff forbidden** |
| **Pagination** | Yes |

**Query parameters:**

| Parameter | Description |
|-----------|-------------|
| `search` | Action, details, user email/name |
| `action` | Exact action filter (e.g. `LOGIN`, `UPLOAD`) |
| `role` | User role filter |
| `orgUnit` or `org_unit` | OrgUnit name, ID, or `Global Access` |
| `start_date` | `YYYY-MM-DD` (inclusive) |
| `end_date` | `YYYY-MM-DD` (inclusive, end of day) |
| `page`, `page_size` | Pagination |

**Timestamp format:** `YYYY-MM-DD HH:MM:SS` (Asia/Manila)

---

#### Create audit log (client-side)

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/audit-logs/` |
| **Auth** | Bearer JWT |

Used by frontend for client-initiated events. Server-side actions use `log_audit()` directly.

**Status: Needs Review** — `ModelViewSet` also exposes UPDATE/DELETE unless blocked elsewhere; verify before use in production.

---

#### Export audit logs Excel

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/audit-logs/export-xlsx/` |
| **Response** | `.xlsx` attachment |

Same filters as list endpoint.

---

#### Audit log analytics (bar chart data)

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/audit-logs/analytics/` |
| **Auth** | Bearer JWT |
| **Roles** | Admin (global), Dept Head (scoped) |

Same query filters as list endpoint (`search`, `action`, `role`, `orgUnit`, `start_date`, `end_date`).

**Success `200`:**

```json
{
  "uploads_by_org_unit": [{ "org_unit": "Headquarters", "count": 12 }],
  "deletes_by_org_unit": [{ "org_unit": "Headquarters", "count": 3 }],
  "edits_by_org_unit": [{ "org_unit": "Headquarters", "count": 5 }]
}
```

---

### 7.10 Recycle Bin API

#### List deleted items

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/recycle-bin` |
| **Auth** | Bearer JWT |
| **Roles** | Admin (global), Dept Head (scoped) |
| **Pagination** | Yes |

**Query parameters:**

| Parameter | Values |
|-----------|--------|
| `type` | `all` (default), `documents`, `document`, `folders`, `folder` |
| `page`, `page_size` | Pagination |

**Response:** Paginated merged list of documents and folders with `deletedAt`, `deletedByFullName`, `orgUnitName`.

---

#### Restore item

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/recycle-bin/restore` |

**Request body:**

```json
{
  "type": "document",
  "id": "15"
}
```

| type | Behavior |
|------|----------|
| `folder` | Restores folder and contained documents |
| `document` | Restores document; fails if parent folder still deleted |

---

#### Permanently delete item

| | |
|---|---|
| **Method** | `DELETE` |
| **Path** | `/api/recycle-bin/delete?type=document&id=15` |

| type | Behavior |
|------|----------|
| `folder` | Hard-deletes folder tree and files |
| `document` | Hard-deletes DB record and media file |

---

### 7.11 Account Settings API

Account settings use existing auth endpoints:

| Action | Endpoint |
|--------|----------|
| Get profile | `GET /api/auth/me` |
| Update full name | `PUT/PATCH /api/users/{id}` with `fullName` (Admin/Dept Head managing users) or **Status: Needs Review** for self-service name update |
| Change password | `POST /api/auth/update-password` |

**Status: Needs Review** — No dedicated self-service profile update endpoint; users may need Admin to update `fullName` via Users API.

---

### 7.12 AI Document Assistant API

**Status: Implemented — depends on OpenRouter configuration.**

#### Chat with assistant

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/ai/chat/` |
| **Auth** | Bearer JWT |

**Request body:**

```json
{
  "query": "list all documents",
  "session_id": "optional-openrouter-session-id"
}
```

**Success `200`:**

```json
{
  "answer": "Here are the first 5 accessible documents I found:\n- ...",
  "matches": [
    {
      "id": 10,
      "title": "report.pdf",
      "code": "01-12551",
      "folder_path": "SDD > Reports",
      "category": "Reports",
      "score": 900,
      "reasons": ["accessible document"]
    }
  ]
}
```

Answers are scoped to the user's accessible documents. See `CHATBOT_CAPABILITIES.md` for supported intents.

---

#### Search preview

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/ai/search-preview/` |
| **Query** | `q=<search text>` |

Returns `{ "matches": [...] }` without LLM answer.

---

### 7.13 Backup Management API

**Status: Implemented — admin role only.**

Provides on-demand database and media file downloads for disaster recovery and migration. Restore is not included in this phase.

#### Download database backup

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/backups/database` |
| **Auth** | Bearer JWT |
| **Role** | `admin` only |

**Success `200`:** SQL file download  
**Filename:** `DFS_DATABASE_YYYYMMDD_HHMMSS.sql`  
**Content-Type:** `application/sql`

**MySQL:** Uses `mysqldump` (requires MySQL client in backend container).  
**SQLite (dev):** SQLite `.dump` output.

**Audit action:** `BACKUP_DATABASE_DOWNLOADED`

**Errors:**

| Code | When |
|------|------|
| `401` | Missing or invalid JWT |
| `403` | Non-admin user (`BACKUP_ACCESS_DENIED` logged) |
| `500` | Backup command failed |

---

#### Download media backup

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/backups/media` |
| **Auth** | Bearer JWT |
| **Role** | `admin` only |

**Success `200`:** ZIP file download  
**Filename:** `DFS_MEDIA_YYYYMMDD_HHMMSS.zip`  
**Content-Type:** `application/zip`

Archives all files under `MEDIA_ROOT` (uploaded PDFs, profile pictures, etc.).

**Audit action:** `BACKUP_MEDIA_DOWNLOADED`

**Errors:** Same as database backup.

---

### 7.14 System Settings API

Singleton configuration for upload limits and **system-wide total storage quota** (all Office Units combined).

`storage_quota_mb` serves two roles:

1. **Physical usage cap** — compared against the sum of all document file sizes; drives upload blocking at 100% and physical-usage notification thresholds.
2. **Top-level allocation pool** — the sum of **top-level** (root) Office Unit `storage_quota_mb` values cannot exceed this limit. Child unit quotas are validated against their **parent's envelope**, not this system pool directly.

Per–Office Unit quotas (`OrgUnit.storage_quota_mb`) are allocation envelopes: a parent with 15 GB may assign 5 GB to a child, leaving 10 GB in the parent's pool (`availableForAllocationMb` on list responses).

**Admin UI presets:** 5 GB, 15 GB, 100 GB, 500 GB, 1 TB, or Custom (any value from 1 MB up to 1 TB / 1048576 MB).

| | |
|---|---|
| **Method** | `GET` / `PATCH` |
| **Path** | `/api/system/settings/` |
| **Auth** | Bearer JWT |

**GET (all roles):** Returns public fields including live storage status:

```json
{
  "upload_limit_mb": 15,
  "storage_quota_mb": 5120,
  "storage_quota_exceeded": false,
  "storage_used_mb": 120.5,
  "storage_remaining_mb": 4999.5,
  "storage_usage_percentage": 2.4,
  "allocated_storage_mb": 4096,
  "allocation_remaining_mb": 1024,
  "allocation_percentage": 80.0
}
```

- `storage_*` fields — physical file usage vs system quota
- `allocated_storage_mb` / `allocation_remaining_mb` / `allocation_percentage` — sum of **top-level** Office Unit quota allocations vs system quota (excludes child units counted under parents)

**GET (admin):** Also includes `updated_at`, plus the same live `storage_*` and `allocated_*` fields as the public response.

**PATCH (admin only):**

```json
{
  "upload_limit_mb": 15,
  "storage_quota_mb": 5120
}
```

`storage_quota_mb` must be between 1 and 1048576 (1 TB).

**Lower bound:** `storage_quota_mb` cannot be set below `max(ceil(storage_used_mb), allocated_storage_mb)` — current file usage and top-level Office Unit allocations. Example `400`:

```json
{
  "storage_quota_mb": [
    "Storage quota cannot be set below current file usage (20480 MB / 20 GB used). Minimum allowed: 20480 MB / 20 GB."
  ]
}
```

Increasing `storage_quota_mb` resets storage threshold notification flags (physical usage and allocation) for thresholds no longer crossed.

**Audit action:** `UPDATE_SYSTEM_SETTINGS`

---

### 7.15 Notifications API

System-wide storage alerts surfaced in the notification bell.

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/notifications/` |
| **Auth** | Bearer JWT |

Returns notifications where `audience=all`, plus `audience=admin` for admin users.

**Success `200`:**

```json
[
  {
    "id": 1,
    "title": "Storage Warning",
    "message": "System storage has reached 80% capacity.\n\nUsed Storage: 400 MB\nRemaining Storage: 100 MB",
    "level": "warning",
    "threshold_percent": 80,
    "audience": "all",
    "created_at": "2026-06-05T10:00:00Z"
  }
]
```

#### Unread count (badge)

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/notifications/unread-count/` |

**Success `200`:** `{ "count": 3 }`

#### Clear notifications

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/notifications/clear/` |
| **Auth** | Bearer JWT |

Deletes all notifications visible to the current user (same audience filter as list: `all` for everyone; admins also see `admin` audience).

**Success `200`:**

```json
{
  "deleted": 2
}
```

Clearing notifications does not reset storage threshold state; alerts will not regenerate until thresholds fire again (e.g. after quota changes).

**Threshold notifications:**

- **Physical usage** — generated at 80%, 90%, 95%, and 100% of global file usage vs `SystemSettings.storage_quota_mb`. Audience: `all` (and `admin` duplicate at 90%).
- **Allocation pool** — generated at 90% and 100% of **top-level** Office Unit quota allocation vs system quota. Audience: `admin` only.

Each threshold fires once until system quota is increased (resets threshold flags).

**Notification levels:** `warning`, `alert`, `critical`, `exceeded`

**Audit actions:** `STORAGE_WARNING_GENERATED`, `STORAGE_ALERT_GENERATED`, `STORAGE_CRITICAL_ALERT_GENERATED`, `STORAGE_QUOTA_EXCEEDED`, `STORAGE_ALLOCATION_ALERT_GENERATED`, `STORAGE_ALLOCATION_EXCEEDED`, `UPLOAD_BLOCKED_STORAGE_QUOTA`

---

## 8. Query Parameters (Summary)

| Parameter | Used in |
|-----------|---------|
| `search` | `/api/documents`, `/api/users`, `/api/org-units/`, `/api/audit-logs/` |
| `page`, `page_size` | Paginated list endpoints |
| `folderId` | `/api/documents` |
| `orgUnitId` | `/api/documents`, `/api/categories`, `/api/users` |
| `includeChildOrgUnits` | `/api/documents` |
| `category` | `/api/documents` (category ID) |
| `role` | `/api/users`, `/api/audit-logs/` |
| `action` | `/api/audit-logs/` |
| `orgUnit`, `org_unit` | `/api/audit-logs/` |
| `start_date`, `end_date` | `/api/audit-logs/` |
| `office_unit`, `officeUnit`, `org_unit` | `/api/dashboard/` |
| `type` | `/api/recycle-bin` |
| `includeInactive` | `/api/org-types/` |
| `q` | `/api/ai/search-preview/` |

No global `ordering` query parameter is implemented on list endpoints.

---

## 9. Pagination

**Class:** `StandardResultsSetPagination`  
**Default page size:** 10  
**Max page size:** 100  
**Query params:** `page`, `page_size`

**Format:**

```json
{
  "count": 100,
  "next": "http://localhost:8000/api/documents?page=2&page_size=10",
  "previous": null,
  "results": []
}
```

**Non-paginated endpoints:** Categories list, Folders list, Org Types list, Folder tree, Dashboard stats.

---

## 10. File Upload Rules

| Rule | Value |
|------|-------|
| Allowed type | PDF only (`.pdf`, `%PDF` header) |
| Max size | Configurable (default **15 MB** via `SystemSettings.upload_limit_mb`) |
| Global storage block | When system used storage ≥ `SystemSettings.storage_quota_mb` |
| Upload endpoints | `POST /api/documents/upload` |
| Storage path | `media/documents/YYYY/MM/DD/<filename>` |
| Required metadata | `folderId`, `categoryId` (with category `code`) |
| Document code | Unique, pattern `^[A-Za-z0-9-]+$`, stored uppercase |
| Description max length | 50 characters |
| Keywords | JSON array of strings |
| Duplicate filename | Rejected within same folder |
| Source values | `Uploaded` (default; legacy rows may show `Scanned`) |

---

## 11. Security Rules

| Rule | Implementation |
|------|----------------|
| JWT required | All endpoints except login, forgot/reset/set password, JWT refresh |
| Role checks | Enforced in views (not a centralized permission class) |
| OrgUnit filtering | Queryset filtering per view |
| Login rate limit | 5/minute per IP |
| Activation email limit | 3/hour per user |
| Password reset | 30-minute token expiry |
| Last admin protection | Cannot deactivate/delete last active Admin |
| Client logout | Clears localStorage only; no server token revocation |
| Sensitive data | Never commit `.env`, JWT secrets, email passwords, or API keys |

---

## 12. Environment Variables Used by API

| Variable | Purpose | Example |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | `<secret>` |
| `DEBUG` | Debug mode | `True` / `False` |
| `ALLOWED_HOSTS` | Allowed Host header values | `localhost,127.0.0.1` |
| `DB_ENGINE` | `sqlite` or `mysql` | `mysql` |
| `DB_NAME` | MySQL database name | `dfs_project` |
| `DB_USER` | MySQL username | `dfs_user` |
| `DB_PASSWORD` | MySQL password | `<secret>` |
| `DB_HOST` | MySQL host | `db` |
| `DB_PORT` | MySQL port | `3306` |
| `SQLITE_NAME` | SQLite path (when `DB_ENGINE=sqlite`) | `db.sqlite3` |
| `EMAIL_BACKEND` | Email backend class | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | SMTP host | `smtp.example.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_USE_TLS` | Enable TLS | `True` |
| `EMAIL_HOST_USER` | SMTP username | `<email>` |
| `EMAIL_HOST_PASSWORD` | SMTP password | `<secret>` |
| `DEFAULT_FROM_EMAIL` | From address | `<email>` |
| `FRONTEND_URL` | Base URL for email links | `http://localhost:5173` |
| `OPENROUTER_API_KEY` | AI assistant API key | `<secret>` |
| `OPENROUTER_MODEL` | LLM model slug | `google/gemini-2.5-flash-lite` |
| `OPENROUTER_BASE_URL` | OpenRouter API base | `https://openrouter.ai/api/v1` |
| `VITE_API_URL` | Frontend API base (Vite) | `http://localhost:8000` |

---

## 13. Frontend Integration Notes

### API client

- Location: `frontend/src/lib/api.ts`
- Base URL: `import.meta.env.VITE_API_URL`
- Token storage: `localStorage.auth_token`
- User storage: `localStorage.auth_user`
- Header: `Authorization: Bearer <token>`

### Auth flow

1. `POST /api/auth/login` → store token + user
2. On app load, `GET /api/auth/me` rehydrates session
3. On `401`, client clears storage and redirects to `/login`
4. On `429`, redirects to `/error/429`
5. On `5xx`, redirects to `/error/500`

### Uploads

Use `api.upload(endpoint, formData)` — do not set `Content-Type` manually.

### Protected routes

Enforced in React router by auth context (`frontend/src/lib/auth-context.tsx`).

### Error handling

```typescript
throw new Error(data.error || data.message || data.detail || "Request failed");
```

---

## 14. Developer Testing Examples

Replace `<TOKEN>`, `<ID>`, and paths as needed.

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your-password"}'
```

### List documents

```bash
curl http://localhost:8000/api/documents?page=1&page_size=10 \
  -H "Authorization: Bearer <TOKEN>"
```

### Upload document

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@./sample.pdf" \
  -F "folderId=3" \
  -F "categoryId=1" \
  -F "code=01-99999" \
  -F 'requisitioners=[{"employeeNumber":"202400123","firstName":"Jane","lastName":"Doe","suffix":""}]' \
  -F "description=Test upload" \
  -F 'keywords=["test","pdf"]'
```

### Create folder

```bash
curl -X POST http://localhost:8000/api/folders \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Folder","orgUnitId":"2"}'
```

### Export audit logs Excel

```bash
curl "http://localhost:8000/api/audit-logs/export-xlsx/?start_date=2026-05-01&end_date=2026-05-31" \
  -H "Authorization: Bearer <TOKEN>" \
  -o audit_logs.xlsx
```

### Refresh JWT

```bash
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<REFRESH_TOKEN>"}'
```

### AI assistant chat

```bash
curl -X POST http://localhost:8000/api/ai/chat/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"query":"how many files do I have?"}'
```

---

## 15. Known Limitations / Needs Review

| Item | Details |
|------|---------|
| Dashboard stats | Role-scoped with subtree aggregation for parent units; admin global or per-unit filter; see §7.2 |
| OrgUnit CRUD permissions | No Admin-only guard in backend; relies on frontend |
| Category/Folder create permissions | No explicit role checks beyond OrgUnit scope |
| AuditLog ViewSet | Full ModelViewSet — verify UPDATE/DELETE exposure |
| Self-service profile update | No dedicated endpoint for user to update own `fullName` |
| Server logout | Not implemented; JWT valid until expiry |
| Token refresh in frontend | Refresh token returned on login but auto-refresh not wired in `api.ts` |
| AI assistant | Requires `OPENROUTER_API_KEY`; falls back to safe message on LLM failure |
| Public registration | Explicitly disabled (`405`) |
| Trailing slash inconsistency | Mixed across routers; match frontend call patterns |
| Document update via PUT/PATCH | Supported by ViewSet but limited UI usage — verify expected fields |

---

## 16. Maintenance Notes

### When routes change

1. Update this file (`docs/API_DOCUMENTATION.md`)
2. Update `backend/config/urls.py` and app `urls.py` comments if needed
3. Update frontend API calls in `frontend/src/lib/api.ts` and page components
4. Update `CHATBOT_CAPABILITIES.md` if AI behavior changes

### Where to look in code

| Concern | Location |
|---------|----------|
| URL routing | `backend/config/urls.py`, `backend/*/urls.py` |
| Request/response shape | `backend/*/serializers.py` |
| Role and scope logic | `backend/documents/permissions.py`, other `views.py` |
| Models | `backend/*/models.py` |
| Auth settings | `backend/config/settings.py` |
| Pagination | `backend/config/pagination.py` |
| Exception handling | `backend/config/exceptions.py` |
| Audit helper | `backend/auditlogs/models.py` → `log_audit()` |
| Frontend API client | `frontend/src/lib/api.ts` |

### Live OpenAPI / Swagger

Installed via `drf-spectacular`:

| URL | Description |
|-----|-------------|
| `GET /api/docs/` | Swagger UI (browse and try endpoints) |
| `GET /api/schema/` | OpenAPI 3 schema JSON |

Use JWT **Authorize** in Swagger with: `Bearer <access_token>` from login.

> Hand-written sections in this file remain the source for role rules and business logic. Generated schema may not document every custom permission or feature flag.

---

## Appendix A — Endpoint Count Summary

| Group | Endpoints documented |
|-------|---------------------|
| Authentication | 9 (+ 2 JWT utilities) |
| Dashboard | 1 |
| Documents | 8 |
| Folders | 7 |
| Categories | 4 |
| Organization Units | 4 |
| Org Types | 4 |
| Users | 9 |
| Audit Logs | 3 |
| Recycle Bin | 3 |
| Account Settings | 3 (via auth/users) |
| AI Assistant | 2 |
| Backup Management | 2 |
| **Total** | **~59 route handlers** |

### Marked Needs Review

- Dashboard stats scoping
- OrgUnit write permissions
- AuditLog ViewSet mutability
- Self-service profile update
- AI assistant (operational dependency on OpenRouter)

### Suggested next improvements

1. Centralize permissions (`IsAdmin`, `IsDeptHeadOrAdmin`, `OrgUnitScopedPermission`) — partial: see `documents/permissions.py`
2. Add server-side logout / token denylist (optional)
3. Wire JWT refresh in frontend before access token expiry
4. Restrict AuditLog ViewSet to `GET` + export actions only
5. Add Admin-only permission to OrgUnit create/update/delete
