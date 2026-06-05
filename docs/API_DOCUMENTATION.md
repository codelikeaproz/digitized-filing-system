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
- Dashboard stats: **global counts** (not filtered by role in current backend)

### Department Head (`dept_head`)

- Document/folder access: own OrgUnit **and child OrgUnits**
- User management: **Staff only**, within assigned OrgUnit
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

```python
# dept_head scope = [org_unit.id] + all child org unit ids
# staff scope = [org_unit.id]
# admin = no filter
```

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
| `office_unit` | `all` (default for admin), Office Unit ID | Admin only |

**Role behavior:**
- **Admin** — `office_unit=all` returns global stats + storage comparison chart data; specific ID returns scoped Office Unit stats
- **Head / Staff** — always scoped to assigned Office Unit; filter param ignored (enforced on backend)

**Success `200` (global):**

```json
{
  "scope": "global",
  "office_unit_name": "All Office Units",
  "office_unit_filter": "all",
  "can_filter_office_units": true,
  "total_documents": 42,
  "uploaded_files": 42,
  "total_org_units": 5,
  "total_users": 18,
  "deleted_files": null,
  "storage": {
    "org_unit_name": "All Office Units",
    "quota_mb": 10240,
    "used_mb": 3200.5,
    "remaining_mb": 7039.5,
    "usage_percentage": 31.3,
    "percent_used": 31.3
  },
  "storage_by_office_unit": [
    {
      "org_unit_id": "1",
      "org_unit_name": "College of Engineering",
      "quota_mb": 5120,
      "used_mb": 2000,
      "remaining_mb": 3120,
      "usage_percentage": 39.1
    }
  ]
}
```

**Success `200` (specific Office Unit):**

```json
{
  "scope": "office_unit",
  "office_unit_id": "5",
  "office_unit_name": "College of Engineering",
  "office_unit_filter": "5",
  "can_filter_office_units": true,
  "total_documents": 10,
  "uploaded_files": 10,
  "total_org_units": null,
  "total_users": 3,
  "deleted_files": 1,
  "storage": {
    "quota_mb": 500,
    "used_mb": 400,
    "remaining_mb": 100,
    "usage_percentage": 80,
    "percent_used": 80
  },
  "storage_by_office_unit": []
}
```

**Storage calculations:** `used_mb`, `remaining_mb`, and `usage_percentage` are computed dynamically from `Document.file_size` and `OrgUnit.storage_quota_mb` (not stored as dashboard fields).

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
| `categoryId` | Yes | Category ID (must match folder OrgUnit if category is scoped) |
| `code` | Yes | Unique document code (letters, numbers, hyphens) |
| `title` | No | Defaults to uploaded filename |
| `requisitioners` | Yes | JSON array string, e.g. `[{"employeeNumber":"202400123","firstName":"Jane","lastName":"Doe","suffix":""}]` (at least one; first/last name required; digits-only employee numbers; no duplicates per document) |
| `requestor` | No | Legacy derived display string (synced server-side from `requisitioners`; do not send on manual upload) |
| `description` | No | Max 50 characters |
| `keywords` | No | JSON array string, e.g. `["keyword1","keyword2"]` |
| `filePath` | No | Display path; defaults to folder full path |
| `source` | No | `Uploaded` (default; legacy rows may show `Scanned`) |

**Success `201`:** Full `DocumentSerializer` object.

**Errors:**

| Status | Example |
|--------|---------|
| `400` | `{"error": "Only PDF files are supported."}` |
| `400` | `{"error": "PDF file exceeds the 50MB limit."}` |
| `400` | `{"message": "Document Code is already used."}` |
| `409` | `{"message": "Document Code is already used."}` |

**PDF validation rules:**

- Extension must be `.pdf`
- File header must start with `%PDF`
- Max size: **50 MB**
- File must not be empty

**Notes:** After upload, PDF text is indexed via `index_document_text()` for AI search.

---

#### Update document metadata

| | |
|---|---|
| **Method** | `PUT` / `PATCH` |
| **Path** | `/api/documents/{id}` |
| **Auth** | Bearer JWT |
| **Scope** | Must be in accessible OrgUnit |

Uses `DocumentSerializer` — code uniqueness validated on update.

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
  "code": "01-12551",
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
- `requestor` in responses is derived as `"emp - name, emp - name"` for backward compatibility
- At least one requisitioner required; employee numbers must be digits only and unique per document

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

**Admin response:** Virtual `All Files` node + OrgUnit hierarchy with nested folders.

**Non-admin response:** Virtual `All Files` node + flat folder tree for accessible OrgUnits.

**Example node:**

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
| **Scope** | OrgUnit-scoped for non-admin |

**Query parameters:**

| Parameter | Description |
|-----------|-------------|
| `orgUnitId` | Filter by OrgUnit |

**Response fields include:** `documentCount`, `inUse` (true if active documents exist).

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

Unique per `(name, org_unit)`.

---

#### Update category

| | |
|---|---|
| **Method** | `PUT` / `PATCH` |
| **Path** | `/api/categories/{id}` |

---

#### Delete category

| | |
|---|---|
| **Method** | `DELETE` |
| **Path** | `/api/categories/{id}` |

**Blocked when:**

- Active documents reference the category

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

**Response includes:** `userCount`, `folderCount`, `documentCount`, `childCount`, `canDelete`, `deleteBlockReason`.

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
  "org_type_id": 2
}
```

**Validation:**

- Name required; unique among siblings
- No circular parent relationships
- Active Org Type required (`org_type_id`)

**Status: Needs Review** — No explicit Admin-only permission check in `OrgUnitViewSet`; any authenticated user can call this endpoint. Frontend restricts to Admin UI.

---

#### Update OrgUnit

| | |
|---|---|
| **Method** | `PUT` / `PATCH` |
| **Path** | `/api/org-units/{id}/` |

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
  "message": "Org Unit deleted successfully"
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

#### Export audit logs CSV

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/audit-logs/export-csv/` |
| **Response** | `text/csv` attachment |

Filename: `audit_logs_YYYY-MM-DD.csv`

Columns: Timestamp, Name, Role, Org Unit, Action, Details

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
| Max size | 50 MB |
| Upload endpoints | `POST /api/documents/upload` |
| Storage path | `media/documents/YYYY/MM/DD/<filename>` |
| Required metadata | `folderId`, `categoryId`, `code` |
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

### Export audit logs CSV

```bash
curl "http://localhost:8000/api/audit-logs/export-csv/?start_date=2026-05-01&end_date=2026-05-31" \
  -H "Authorization: Bearer <TOKEN>" \
  -o audit_logs.csv
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
| Dashboard stats | No role-based scoping — all users see global counts |
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
| Audit Logs | 4 |
| Recycle Bin | 3 |
| Account Settings | 3 (via auth/users) |
| AI Assistant | 2 |
| **Total** | **~58 route handlers** |

### Marked Needs Review

- Dashboard stats scoping
- OrgUnit write permissions
- AuditLog ViewSet mutability
- Self-service profile update
- AI assistant (operational dependency on OpenRouter)

### Suggested next improvements

1. Centralize permissions (`IsAdmin`, `IsDeptHeadOrAdmin`, `OrgUnitScopedPermission`) — partial: see `documents/permissions.py`
2. Scope dashboard stats by role
3. Add server-side logout / token denylist (optional)
4. Wire JWT refresh in frontend before access token expiry
5. Restrict AuditLog ViewSet to `GET` + export actions only
6. Add Admin-only permission to OrgUnit create/update/delete
