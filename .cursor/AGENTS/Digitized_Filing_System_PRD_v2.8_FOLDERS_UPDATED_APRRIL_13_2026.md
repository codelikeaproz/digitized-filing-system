# 📄 Product Requirements Document
## Digitized Filing System

| Field | Details |
|-------|---------|
| **Version** | 2.6 — DRAFT |
| **Prepared For** | Stakeholders & Development Team |
| **Deployment** | LAN-Based Desktop Environment (Phase 1) |
| **Target Users** | Medium Organization — 21 to 100 Users |
| **Deployment Target** | Short-term — 1 to 3 Months |
| **Status** | 🟡 DRAFT — Pending Final Review |
| **Date** | March 2026 |

---

## 1. Executive Summary

The Digitized Filing System is a LAN-based web application designed to manage scanned and approved documents within departments. The system enables secure uploading, categorization, routing, tracking, and archiving of soft-copy documents.

The platform replaces manual USB/email-based file sharing and provides structured digital storage with full accountability and audit tracking. It is optimized for medium-sized organizations of 21 to 100 users on a desktop-first LAN environment, with a Phase 2 roadmap targeting internet-based cloud access.

---

## 2. Problem Statement

The following operational issues were identified in the current document handling workflow:

- Documents are scanned and stored manually with no standardized process.
- Files are saved in inconsistent folders without categorization standards.
- No tracking of who accessed, viewed, or downloaded documents.
- Risk of duplication, misplacement, or unauthorized access to sensitive files.
- No centralized monitoring, version history, or audit log.
- Departments rely on USB transfers and email — both slow and insecure.

This system aims to centralize and secure document handling across all departments within the organization.

---

## 3. Objectives

- Centralize approved scanned documents in a single, structured repository.
- Standardize file categorization and naming conventions across departments.
- Enable user-based and role-based access control.
- Provide permission-based document routing between users and departments.
- Implement full audit logging for transparency and accountability.
- Optimize performance for desktop-based LAN usage with 21–100 concurrent users.
- Lay the groundwork for a future Phase 2 cloud-based deployment.

---

## 4. Scope

### 4.1 In Scope — MVP (Phase 1)

- Login-based authentication with session management
- Department-based access control
- Upload scanned documents (PDF primary; DOCX, XLSX optional)
- Document categorization (Memo, Reports, Approved Docs, Letters, Forms, Others)
- Send documents to a specific user or department
- Permission levels: Read-only, Editable, Re-share, Full Control
- Inbox and Sent document views
- Search and filtering by category, date, sender, department, and status
- Audit trail logging for all key events
- LAN deployment — Desktop only (1366px+ resolution)

### 4.2 Out of Scope — Phase 2 (Future)

- Internet-based cloud access *(planned Phase 2 priority)*
- Mobile optimization (iOS / Android)
- Real-time collaborative document editing
- AI-powered document classification
- External system integrations (HR, ERP)
- E-signature integration

---

## 5. User Roles

### 5.1 Admin
- Manage users, roles, and departments
- Full system access — all documents and features
- View complete audit logs and system reports
- Manage document categories

### 5.2 Staff User
- One designated user account per department *(current phase)*
- Upload scanned documents on behalf of their department
- Send documents to users or departments with defined permissions
- View personal inbox and sent items
- Search and filter accessible documents

> **Note:** The current phase assigns one user account per department. Multi-user per department support may be revisited in a future phase based on operational needs.

### 5.3 Department Head *(Optional Role)*
- View the full department inbox
- Monitor document activity within their department
- Forward or re-route documents as needed

---

## 6. Functional Requirements

### 6.1 Authentication
- Users must log in using unique credentials (username and password).
- Session-based authentication with automatic timeout.
- Role-based authorization enforced on every route.

### 6.2 Document Upload

- Accepted formats: PDF (primary), DOCX, XLSX (optional).
- Configurable file size limit set by Admin.
- Category must be assigned before document submission — category also determines the NAS folder destination.
- Upload timestamps and uploader identity are automatically recorded.
- **Upload UI:** Drag-and-drop file zone (similar to Windows Explorer or Google Drive) — users can drag files directly into the upload area or click to browse.
- **Package:** `react-dropzone` (v15.0.0, MIT License, 7.8M weekly downloads)

**Installation:**
```bash
npm install --save react-dropzone
```

**Usage pattern:**
```javascript
import { useDropzone } from 'react-dropzone';

function DocumentUpload() {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxSize: 20971520, // 20MB — configurable by Admin
    onDrop: (acceptedFiles) => {
      // Send to Django REST API via Axios
    }
  });

  return (
    <div {...getRootProps()} className={isDragActive ? 'dropzone active' : 'dropzone'}>
      <input {...getInputProps()} />
      <p>Drag and drop files here, or click to browse</p>
    </div>
  );
}
```


### 6.2.1 Folder Hierarchy & Drive-Style Navigation

The system shall support a **hierarchical folder structure** similar to Google Drive, where folders can contain subfolders and documents with **unlimited nesting**. This structure is intended for logical organization and navigation of records inside the application. The folder hierarchy is implemented using a **self-referencing parent-child relationship**.

#### Folder Model Standard
- Each folder has one unique primary key: `id`
- Each folder may optionally reference one parent folder through `parent_id`
- Root folders must use `parent_id = NULL` — never `0`
- A folder may contain:
  - zero or more child folders
  - zero or more documents
- A document belongs to one folder at a time through `folder_id`

#### Relational Design
**folders**
- `id` — Primary Key
- `name` — Folder name
- `parent_id` — Nullable Foreign Key → `folders.id`
- `department_id` — Foreign Key → `departments.id` (if folder ownership is department-scoped)
- `created_by` — Foreign Key → `users.id`
- `created_at`
- `updated_at`

**documents**
- `id` — Primary Key
- `title`
- `file_path`
- `folder_id` — Foreign Key → `folders.id`
- `uploaded_by` — Foreign Key → `users.id`
- `created_at`
- `updated_at`

#### Design Rule
The hierarchy requires only:
- one **Primary Key**: `id`
- one **self-referencing Foreign Key**: `parent_id`

Additional foreign keys are only required when connecting folders or documents to other entities such as users, departments, categories, audit logs, or permissions.

#### Example Tree
```text
SDD
└── Hanging Cabinet 1
    └── Compartment 1 - HC1
        ├── Human Resource Folder
        └── Projects
```

#### Why this design is correct
- Supports unlimited folder depth
- Matches common drive-style navigation patterns
- Simple to understand and implement
- Compatible with Django ORM and recursive UI rendering
- Easier to maintain than creating separate tables for cabinet, compartment, folder, and subfolder levels

#### Constraints & Best Practices
- Prevent a folder from becoming its own parent
- Prevent circular references in the hierarchy
- Enforce unique folder names **within the same parent** if required by business rules
- Index `parent_id` and `folder_id` for performance
- Use soft delete or archive flags if deleted folders/documents must remain auditable
- If full breadcrumb or deep tree queries become heavy at scale, consider adding a cached materialized path later as an optimization — not as the initial MVP structure


### 6.3 Document Categorization

Documents are classified using **two dimensions**:

**By Type** (predefined categories):
- Memo
- Approved Documents
- Reports
- Letters
- Forms
- Others

**By Year** (archive year):
- Documents are tagged with a filing year upon upload (e.g., 2023, 2024, 2025).
- Users can browse and filter the document archive by year.
- The system defaults to the current year on upload but allows Admin to assign a different year for backdated documents.

> **NAS Folder Routing:** The selected category determines which folder on the NAS the document is physically stored in. Each category maps to a dedicated NAS folder (e.g., `Memos/`, `Reports/`, `Approved_Documents/`). Filing year is used as a subfolder within the category folder (e.g., `Reports/2025/`). Admin manages the category-to-folder mapping.

> Admin can add, edit, or remove document type categories. Filing years are system-managed and auto-populated.

### 6.4 Document Routing
- Sender can route a document to a specific user OR an entire department.
- Sender selects a permission level at time of sending.
- Multiple recipients are supported.

### 6.5 Permission Control

Since the system stores only **approved and finalized documents**, editing is not permitted at the user level. All routed documents carry a single enforced permission:

| Permission Level | Allowed Actions |
|-----------------|-----------------|
| **Read-only** | View + Download only — no editing, commenting, or re-sharing |

> All users receiving a document can only view and download it. Modifications to document records are restricted to Admin only. This ensures the integrity of approved documentation is preserved at all times.

### 6.6 Search & Filtering

Users can filter the document list by:

- Category (Memo, Reports, Approved Docs, etc.)
- **Filing Year** (e.g., 2023, 2024, 2025)
- Date range (upload or received date)
- Sender name or username
- Department
- Status (Not Sent, Sent, Received, Archived)

> **Implementation Standard — Dynamic AJAX, No Apply/Clear Buttons:**
> All search and filtering is **real-time and dynamic**. Results update automatically as the user types or changes a filter — there are no "Apply" or "Clear" buttons. Every filter input (dropdown, date picker, search field) triggers an AJAX call to the Django REST API instantly on change, and the DataTable refreshes in place. This eliminates manual submission steps and provides a fluid, responsive experience similar to modern web applications.


### 6.7 Status Tracking

Each document carries one of the following statuses:

- **Not Sent** — Document uploaded but not yet routed to any recipient
- **Sent** — Document dispatched by the sender to a user or department
- **Received** — Document delivered to and acknowledged by the recipient
- **Archived** — Document moved to long-term storage

### 6.8 Audit Logging

The system automatically records:

- Login and logout events (user, timestamp, IP)
- Document upload events
- Document send / routing events
- Document download events
- Status change events
- Permission modifications

> Admin can view, filter, and export audit logs from the admin panel.

---

## 7. Non-Functional Requirements

### 7.1 Performance
- Optimized for LAN network speeds (no internet dependency in Phase 1).
- Must support 21–100 concurrent departmental users without degradation.
- Document retrieval should complete within 2 seconds on LAN.

### 7.2 Security
- Role-based access control enforced at every API endpoint — not just the frontend.
- No public internet exposure in Phase 1 — LAN only.
- Server hosted internally, accessible only within the office network.
- Passwords hashed using Django's PBKDF2 + SHA256 — never stored in plain text.
- JWT access tokens expire after 8 hours (one workday); refresh tokens blacklisted on logout.
- All credentials and secrets loaded from environment variables — never hardcoded.
- `DEBUG = False` enforced in production at all times.
- File uploads validated server-side for MIME type and file size — not just client-side.
- All database queries use Django ORM — raw SQL with user input is strictly prohibited.
- See **Section 11 — Security Risks & Validation Standards** for full implementation details.

### 7.3 Usability
- Desktop-first design targeting 1366px and above resolutions.
- Clean sidebar navigation layout with minimal learning curve.
- Accessible on Chrome and Edge browsers without plugin requirements.

### 7.4 Reliability
- Daily automated database backups.
- Media file storage backup policy — weekly full backup.
- System uptime target: 99% during business hours.

---

## 8. Technical Architecture

The system uses a **decoupled architecture** — Django serves as a REST API backend, and React runs as a fully independent frontend application. They communicate exclusively via HTTP API calls using Axios.

### 8.1 Backend — Django REST API
- **Framework:** Django + Django REST Framework (DRF)
- **Architecture:** API-only — no Django Templates used for UI rendering
- **Database:** MySQL
- **Authentication:** Token-based or JWT authentication (via DRF SimpleJWT)
- **Media Storage:** NAS (Network Attached Storage) — One Office to multiple NAS units
  - Each category maps to a dedicated NAS folder; filing year used as subfolder
  - Django resolves the NAS path based on the document's category and year at upload time
  - Example structure: `NAS:/Memos/2025/filename.pdf`
- **WSGI Server:** Gunicorn
- **Reverse Proxy:** Nginx (LAN deployment)
- **CORS:** django-cors-headers configured for React frontend origin

### 8.2 Frontend — React Application
- **Framework:** React (Vite or Create React App)
- **UI Component Library:** ShadCN/UI (built on Radix UI primitives + Tailwind CSS)
- **HTTP Client:** Axios (for all API communication with Django backend)
- **File Upload:** `react-dropzone` (drag-and-drop file zone)
- **State Management:** React Context API or Zustand (TBD)
- **Routing:** React Router DOM
- **Styling:** Tailwind CSS (used alongside ShadCN components)

### 8.3 Frontend Implementation Standards

---

#### 8.3.1 DataTables — Server-Side Processing (Required for All Table Views)

Every page that renders tabular data **must use DataTables in server-side processing mode**. This is a non-negotiable standard across the entire application.

**Why server-side mode?**
In client-side mode, DataTables loads the entire dataset at once — this is a performance problem at scale. With server-side mode, DataTables sends an AJAX request to the Django API and receives only the rows needed for the current page (e.g., 10 rows). This means:

- The database only processes the **current page query** — not the full table
- Queries are limited to **10 rows per request** by default (configurable)
- Sorting, filtering, and pagination are all handled by the Django backend
- The frontend never holds a large dataset in memory
- System load is minimized — critical for a 21–100 user LAN environment

**How it works:**
```
User interacts with table (page, sort, search)
        ↓
DataTables sends AJAX request to Django API
        ↓
Django queries MySQL — only the requested rows (LIMIT 10 OFFSET N)
        ↓
Django returns JSON: { data: [...10 rows], recordsTotal, recordsFiltered }
        ↓
DataTables re-renders only those rows
```

---

#### 8.3.2 Django Backend — `django-rest-framework-datatables`

Since this project uses **Django REST Framework**, the recommended package is `django-rest-framework-datatables` — it plugs directly into existing DRF ViewSets and serializers with minimal changes.

**Installation:**
```bash
pip install djangorestframework-datatables
```

**Add to settings.py:**
```python
INSTALLED_APPS = [
    ...
    'rest_framework',
    'rest_framework_datatables',
]

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework_datatables.renderers.DatatablesRenderer',  # add this
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework_datatables.filters.DatatablesFilterBackend',  # add this
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework_datatables.pagination.DatatablesPageNumberPagination',
    'PAGE_SIZE': 10,   # rows per page — limits every query to 10 rows
}
```

**DRF ViewSet — minimal changes needed:**
```python
# documents/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_datatables.filters import DatatablesFilterBackend
from .models import Document
from .serializers import DocumentSerializer

class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class   = DocumentSerializer
    filter_backends    = [DatatablesFilterBackend]

    def get_queryset(self):
        # Always scope to requesting user — security standard
        return Document.objects.filter(
            deliveries__recipient=self.request.user
        ).select_related('category', 'uploader', 'uploader__department').order_by('-created_at')
```

**Serializer — define `datatables_always_serialize` for searchable fields:**
```python
# documents/serializers.py
from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    category_name   = serializers.CharField(source='category.name', read_only=True)
    uploader_name   = serializers.CharField(source='uploader.full_name', read_only=True)
    department_name = serializers.CharField(source='uploader.department.name', read_only=True)

    class Meta:
        model  = Document
        fields = ['id', 'title', 'category_name', 'filing_year',
                  'uploader_name', 'department_name', 'status', 'created_at']
        # These fields are always included in DataTables responses for searching
        datatables_always_serialize = ('id',)
```

**URL — append `?format=datatables` to activate server-side mode:**
```python
# documents/urls.py
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
urlpatterns = router.urls

# DataTables will call: GET /api/documents/?format=datatables&draw=1&start=0&length=10
```

---

#### 8.3.3 React Frontend — `datatables.net-react` with Server-Side Mode

**Installation:**
```bash
npm install --save datatables.net-react datatables.net-dt
```

**Server-side DataTable component with dynamic AJAX filters:**
```javascript
import { useRef, useEffect } from 'react';
import DataTable from 'datatables.net-react';
import DT from 'datatables.net-dt';
import api from '../api/axiosInstance';

DataTable.use(DT);

function DocumentTable({ filters }) {
  const tableRef = useRef(null);

  // When filters change, redraw the table — triggers new AJAX request
  useEffect(() => {
    if (tableRef.current) {
      tableRef.current.dt().ajax.reload();
    }
  }, [filters]);

  return (
    <DataTable
      ref={tableRef}
      columns={[
        { title: 'Title',       data: 'title' },
        { title: 'Category',    data: 'category_name' },
        { title: 'Year',        data: 'filing_year' },
        { title: 'Sender',      data: 'uploader_name' },
        { title: 'Department',  data: 'department_name' },
        { title: 'Status',      data: 'status' },
        { title: 'Actions',     data: 'id', orderable: false },
      ]}
      options={{
        serverSide: true,           // Enable server-side processing
        processing: true,           // Show loading indicator during AJAX
        pageLength: 10,             // Default 10 rows per page
        lengthMenu: [10, 25, 50],   // User can change page size
        ordering: true,
        responsive: true,
        ajax: {
          url: `${import.meta.env.VITE_API_URL}/api/documents/?format=datatables`,
          type: 'GET',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`
          },
          // Attach dynamic filters to every DataTables AJAX request
          data: (params) => {
            if (filters.category)    params.category    = filters.category;
            if (filters.filing_year) params.filing_year = filters.filing_year;
            if (filters.status)      params.status      = filters.status;
            if (filters.department)  params.department  = filters.department;
            return params;
          },
          error: () => {
            // ShadCN toast for AJAX errors
            toast({ title: 'Error', description: 'Failed to load documents.', variant: 'destructive' });
          }
        },
        language: {
          processing:  'Loading documents...',
          zeroRecords: 'No documents found.',
          search:      'Search:',
        }
      }}
      className="display w-full"
    />
  );
}
```

**Dynamic filter inputs — no Apply/Clear buttons, real-time AJAX:**
```javascript
import { useState } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import DocumentTable from './DocumentTable';

export default function DocumentsPage() {
  const [filters, setFilters] = useState({
    category: '',
    filing_year: '',
    status: '',
    department: '',
  });

  // Each change instantly updates filters → triggers DataTable AJAX reload
  const handleFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex gap-3 flex-wrap">

        {/* Category filter — triggers AJAX on change, no button needed */}
        <Select onValueChange={(val) => handleFilter('category', val)}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Categories</SelectItem>
            <SelectItem value="memo">Memo</SelectItem>
            <SelectItem value="report">Reports</SelectItem>
            <SelectItem value="letter">Letters</SelectItem>
            <SelectItem value="approved">Approved Documents</SelectItem>
            <SelectItem value="form">Forms</SelectItem>
          </SelectContent>
        </Select>

        {/* Year filter */}
        <Select onValueChange={(val) => handleFilter('filing_year', val)}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Years" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Years</SelectItem>
            <SelectItem value="2025">2025</SelectItem>
            <SelectItem value="2024">2024</SelectItem>
            <SelectItem value="2023">2023</SelectItem>
          </SelectContent>
        </Select>

        {/* Status filter */}
        <Select onValueChange={(val) => handleFilter('status', val)}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Statuses</SelectItem>
            <SelectItem value="not_sent">Not Sent</SelectItem>
            <SelectItem value="sent">Sent</SelectItem>
            <SelectItem value="received">Received</SelectItem>
            <SelectItem value="archived">Archived</SelectItem>
          </SelectContent>
        </Select>

      </div>

      {/* Table auto-reloads when filters state changes */}
      <DocumentTable filters={filters} />
    </div>
  );
}
```

> **No Apply or Clear buttons** — each dropdown change immediately fires a new server-side AJAX request. The DataTable re-renders with filtered results from the Django API. This is intentional by design for this project.

---

#### 8.3.4 Query Optimization — Django Backend

With server-side DataTables, Django receives parameters from DataTables (`start`, `length`, `search[value]`, `order[0][column]`, etc.) and must translate them into efficient ORM queries.

**Always use `select_related` and `prefetch_related` to avoid N+1 queries:**
```python
# ✅ CORRECT — single query with JOIN instead of N+1
Document.objects.filter(
    deliveries__recipient=request.user
).select_related(
    'category',
    'uploader',
    'uploader__department'
).order_by('-created_at')

# ❌ WRONG — this causes N+1: one query per row to get category, uploader, etc.
Document.objects.filter(deliveries__recipient=request.user)
```

**Page size is enforced at 10 rows per API call** via `PAGE_SIZE = 10` in `REST_FRAMEWORK` settings. DataTables sends `length=10` (or 25/50 if user changes it) and Django applies `LIMIT` and `OFFSET` accordingly in the SQL query — the database never returns the full table.



### 8.4 API Communication
- All frontend-backend communication happens via RESTful API endpoints.
- Axios handles request/response, auth token injection via interceptors, and error handling.
- API responses returned in JSON format.
- Authentication token stored in HTTP-only cookies or localStorage (to be finalized in security review).

### 8.5 Environment
- **Clients:** Windows Desktop — Chrome or Edge browser (1366px+ resolution)
- **Backend Server:** Internal LAN — Django + Gunicorn + Nginx
- **Frontend Served:** Via Nginx static file serving or separate Node dev server (production: built React bundle served by Nginx)
- **Phase 2 Target:** Cloud-hosted server with internet-based access

---

### 8.6 Development Do’s & Don’ts — React + Django (Required)

The following implementation rules are mandatory for this project. They are intended to keep the codebase readable, predictable, secure, and easy to maintain as the Digitized Filing System grows from MVP to Phase 2.

#### 8.6.1 React Frontend — Do’s

- Keep components focused on a single responsibility. Example: `DocumentTable.jsx` handles table rendering; `DocumentFilters.jsx` handles filter UI; `UploadDocumentForm.jsx` handles upload interaction.
- Use clear verb-based function names that describe the exact action:
  - `fetchDocuments`
  - `uploadDocument`
  - `routeDocumentToDepartment`
  - `handleFilterChange`
  - `handleLogout`
- Keep API calls centralized in a single Axios layer (e.g., `axios-instance.js` or service files) instead of scattering raw requests across many components.
- Keep page-level state in page components and pass only the needed props to child components.
- Use `useEffect` only for real side effects such as fetching documents, reloading DataTables, or checking authentication state.
- Keep render logic clean by extracting repeated UI into small reusable components such as `StatusBadge`, `PermissionBadge`, and `PageHeader`.
- Show loading, empty, and error states clearly on every major page:
  - Document list loading
  - No results found
  - Upload failed
  - Unauthorized access
- Lazy load page-level routes and heavy modules to reduce the initial bundle size for LAN desktop users.

#### 8.6.2 React Frontend — Don’ts

- Do not place upload logic, filter logic, table logic, modal logic, and API logic all inside one large page component.
- Do not use vague function names such as `doStuff`, `processData`, `sample`, `clickHere`, or `handleEverything`.
- Do not hardcode API URLs inside components. Always use `VITE_API_URL`.
- Do not store duplicated document state in too many places. Use one clear source of truth per screen.
- Do not use `dangerouslySetInnerHTML` anywhere in the project.
- Do not lazy load tiny UI-only pieces such as simple buttons, badges, or one-line utility components.
- Do not make every component stateful if the data can be passed via props.
- Do not call protected API endpoints directly from random utility code without the shared Axios auth handling.

**React example — preferred function structure:**
```javascript
export default function DocumentsPage() {
  const [filters, setFilters] = useState({
    category: '',
    filing_year: '',
    status: '',
    department: '',
  });

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="p-6 space-y-4">
      <DocumentFilters filters={filters} onChange={handleFilterChange} />
      <DocumentTable filters={filters} />
    </div>
  );
}
```

**React anti-pattern — avoid this:**
```javascript
export default function DocumentsPage() {
  const handleEverything = async () => {
    // fetch documents
    // upload document
    // archive document
    // open modal
    // validate form
    // route to department
    // update search filters
  };

  return <div>...</div>;
}
```

#### 8.6.3 Django Backend — Do’s

- Keep business rules in the backend even if the frontend already validates the form.
- Scope every document queryset to the authenticated user, department, or role before returning results.
- Keep views and ViewSets focused. A document list endpoint should list documents; routing logic should be handled in a dedicated action or service layer.
- Use serializers for validation and response shaping instead of putting all validation inside views.
- Reuse helper functions for repeated security and file logic such as:
  - `validate_uploaded_file`
  - `generate_nas_filename`
  - `get_user_accessible_documents`
- Use Django ORM with `select_related()` and `prefetch_related()` for document, category, uploader, and department lookups.
- Return consistent JSON responses for success and error states.
- Keep audit logging automatic for upload, routing, download, login, logout, and archive events.

#### 8.6.4 Django Backend — Don’ts

- Do not trust the frontend to enforce permissions, roles, or file validation.
- Do not expose unscoped `Document.objects.all()` queries on authenticated endpoints.
- Do not place unrelated logic in a single view such as login handling, upload processing, and document routing all together.
- Do not use raw SQL with user input.
- Do not return serializer `fields = '__all__'` for sensitive models.
- Do not hardcode NAS paths, token expiry values, or file size limits directly across multiple files.
- Do not bypass audit logging for important document actions.
- Do not rely only on hidden buttons in React for security; the API must enforce all permissions.

**Django example — preferred queryset scoping:**
```python
class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(
            deliveries__recipient=self.request.user
        ).select_related(
            'category',
            'uploader',
            'uploader__department'
        ).order_by('-created_at')
```

**Django anti-pattern — avoid this:**
```python
def get_queryset(self):
    return Document.objects.all()
```

#### 8.6.5 Function Readability Standard

For both React and Django, every function in this project should follow these rules:

- One function should perform one clear responsibility only.
- The name must reveal the action without reading the body.
- Inputs and outputs should be obvious from the function signature.
- Repeated logic should be extracted into reusable helpers or hooks.
- A future developer must understand the purpose of the function in less than 10 seconds.

**Preferred examples from this project context:**
```javascript
fetchDocuments
uploadDocument
archiveDocument
handleFilterChange
handleDocumentSend
handleLogout
```

```python
validate_uploaded_file
generate_nas_filename
get_user_accessible_documents
send_document_to_department
archive_document
log_document_download
```

---

### 8.7 Frontend Code Splitting & Lazy Loading Standard

To improve perceived performance and reduce the initial React bundle size, the frontend must implement lazy loading for page-level routes and other heavy modules. This is especially useful for the Digitized Filing System because most users will not open every page during the same session.

#### 8.7.1 Lazy Loading Goals for This Project

- Reduce first-load bundle size on login and dashboard pages.
- Avoid loading heavy modules such as DataTables, audit logs, and document management screens before they are needed.
- Keep the initial application startup fast for LAN desktop users on Chrome and Edge.
- Improve maintainability by separating route-level code into independent chunks.

#### 8.7.2 What Must Be Lazy Loaded

The following page-level modules should be lazy loaded by default:

- `LoginPage`
- `DashboardPage`
- `DocumentsPage`
- `InboxPage`
- `SentItemsPage`
- `ArchivePage`
- `AuditLogsPage`
- `AdminUsersPage`
- `SettingsPage`

Heavy feature modules may also be lazy loaded when appropriate:

- DataTables-based table views
- Audit log export module
- Large analytics or reporting screens
- Admin-only management pages

#### 8.7.3 What Must NOT Be Lazy Loaded

The following should remain eagerly loaded unless future profiling proves otherwise:

- Top-level app shell
- Authentication provider / auth context
- Protected route wrapper
- Sidebar navigation shell
- Small shared UI elements such as buttons, badges, and icon wrappers
- Tiny helper functions and constants

#### 8.7.4 Route-Level Lazy Loading Pattern

```javascript
import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import AppShell from './layouts/AppShell';

const LoginPage      = lazy(() => import('./pages/LoginPage'));
const DashboardPage  = lazy(() => import('./pages/DashboardPage'));
const DocumentsPage  = lazy(() => import('./pages/DocumentsPage'));
const InboxPage      = lazy(() => import('./pages/InboxPage'));
const SentItemsPage  = lazy(() => import('./pages/SentItemsPage'));
const ArchivePage    = lazy(() => import('./pages/ArchivePage'));
const AuditLogsPage  = lazy(() => import('./pages/AuditLogsPage'));
const AdminUsersPage = lazy(() => import('./pages/AdminUsersPage'));

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="p-6">Loading page...</div>}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="documents" element={<DocumentsPage />} />
            <Route path="inbox" element={<InboxPage />} />
            <Route path="sent-items" element={<SentItemsPage />} />
            <Route path="archive" element={<ArchivePage />} />
            <Route path="audit-logs" element={<AuditLogsPage />} />
            <Route path="admin/users" element={<AdminUsersPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
```

#### 8.7.5 Page Export Rule

Every lazy-loaded page module must use a default export:

```javascript
export default function DocumentsPage() {
  return <div>Documents Page</div>;
}
```

#### 8.7.6 Loading UX Standard

When a page is lazy loaded:

- Show a simple fallback loader immediately.
- Do not leave the content area blank.
- Keep the sidebar or app shell visible if already loaded.
- Use a consistent loading message or spinner style across all routes.

Example:
```javascript
<Suspense fallback={<PageLoader label="Loading documents..." />}>
  <DocumentsPage />
</Suspense>
```

#### 8.7.7 Lazy Loading Notes for DataTables Pages

Pages that use DataTables and dynamic AJAX filtering are ideal lazy-loading targets because they are heavier than simple static pages. For this project, `DocumentsPage`, `InboxPage`, `SentItemsPage`, and `AuditLogsPage` should be prioritized.

**Rule:** lazy load the page container first; then initialize DataTables only when the user navigates to that page.

#### 8.7.8 Recommended Frontend Folder Structure

```bash
src/
  api/
    axios-instance.js
  components/
    DocumentFilters.jsx
    DocumentTable.jsx
    ProtectedRoute.jsx
    StatusBadge.jsx
  layouts/
    AppShell.jsx
  pages/
    LoginPage.jsx
    DashboardPage.jsx
    DocumentsPage.jsx
    InboxPage.jsx
    SentItemsPage.jsx
    ArchivePage.jsx
    AuditLogsPage.jsx
    AdminUsersPage.jsx
  hooks/
    use-document-filters.js
  App.jsx
```

#### 8.7.9 Implementation Rule

Lazy loading is a required frontend optimization standard for this project’s route-level pages. It should be implemented early in development so the routing structure, loading states, and page organization remain consistent from the start of the build phase.

---

## 9. Naming Conventions & Code Style Standards

Consistent naming conventions are a **required standard** for this project — not a suggestion. Since this project uses two separate codebases (Django backend and React frontend), each with its own language conventions, the rules are defined per layer. All developers must follow these standards from day one to ensure readability, maintainability, and smooth collaboration.

> **Core principle:** Names must describe *what a thing is or does* — not *how it works internally*. A future developer reading the code should understand the purpose of any variable, function, file, or class without needing to trace through the logic.

---

### 9.1 Naming Case Types Reference

| Case | Format | Example |
|------|--------|---------|
| `snake_case` | lowercase, words separated by underscores | `filing_year`, `get_document` |
| `PascalCase` | every word capitalized, no separators | `DocumentSerializer`, `UserProfile` |
| `camelCase` | first word lowercase, subsequent words capitalized | `fetchDocuments`, `filingYear` |
| `kebab-case` | lowercase, words separated by hyphens | `document-list.jsx`, `auth-context.jsx` |
| `SCREAMING_SNAKE_CASE` | all uppercase, words separated by underscores | `MAX_FILE_SIZE_MB`, `ALLOWED_MIME_TYPES` |

---

### 9.2 Django Backend — Naming Standards

#### Models & Classes
- Use **`PascalCase`** for all model names, serializers, views, and classes.
- Model names must be **singular nouns** — never plural.

```python
# ✅ CORRECT
class Document(models.Model): ...
class DocumentSerializer(serializers.ModelSerializer): ...
class DocumentDetailView(RetrieveAPIView): ...
class CustomUser(AbstractBaseUser): ...

# ❌ WRONG
class documents(models.Model): ...       # lowercase
class DocumentsSerializer(): ...         # plural
class docSerializer(): ...               # abbreviated, unclear
```

#### Model Fields & Variables
- Use **`snake_case`** for all model fields, local variables, and function parameters.
- Be descriptive — avoid single letters or cryptic abbreviations.

```python
# ✅ CORRECT
filing_year     = models.IntegerField()
uploaded_by     = models.ForeignKey(CustomUser, ...)
nas_folder_path = models.CharField(max_length=500)
is_active       = models.BooleanField(default=True)
date_uploaded   = models.DateTimeField(auto_now_add=True)

# ❌ WRONG
fy   = models.IntegerField()      # unclear abbreviation
u    = models.ForeignKey(...)     # single letter
path = models.CharField(...)      # too vague — path to what?
d    = models.DateTimeField(...)  # single letter
```

#### Functions & Methods
- Use **`snake_case`** for all functions and methods.
- Start method names with a **verb** that describes the action: `get_`, `create_`, `validate_`, `send_`, `upload_`, `archive_`, `fetch_`.

```python
# ✅ CORRECT
def get_documents_by_department(user):  ...
def validate_uploaded_file(file):       ...
def send_document_to_user(doc, recipient): ...
def archive_document(document_id):      ...

# ❌ WRONG
def documents(user):       ...  # no verb, unclear action
def fileCheck(file):       ...  # camelCase in Python — wrong convention
def process(doc, user):    ...  # too vague — process what?
def doStuff(d):            ...  # meaningless name
```

#### Constants
- Use **`SCREAMING_SNAKE_CASE`** for all constants and configuration values.

```python
# ✅ CORRECT
MAX_FILE_SIZE_MB    = 20
ALLOWED_MIME_TYPES  = ['application/pdf', '...']
NAS_BASE_PATH       = '/mnt/nas/documents'
TOKEN_EXPIRY_HOURS  = 8

# ❌ WRONG
maxFileSize = 20          # camelCase — not Python convention for constants
max_file    = 20          # snake_case — unclear it's a constant
MaxFileSizeMb = 20        # PascalCase — reserved for classes
```

#### URL Patterns & API Endpoints
- Use **`kebab-case`** for all URL paths — lowercase, hyphen-separated.
- Use plural nouns for resource collections.

```python
# ✅ CORRECT
path('api/documents/',              DocumentListView.as_view()),
path('api/documents/<int:pk>/',     DocumentDetailView.as_view()),
path('api/audit-logs/',             AuditLogListView.as_view()),
path('api/filing-years/',           FilingYearListView.as_view()),

# ❌ WRONG
path('api/getDocuments/',    ...)   # verb in URL — not RESTful
path('api/document_list/',   ...)   # underscores in URL
path('api/Doc/',             ...)   # capitalized
```

#### Django App & File Names
- App folder names: **`snake_case`** (e.g., `audit_logs/`, `filing_years/`)
- Python files: **`snake_case`** (e.g., `document_serializer.py`, `upload_validators.py`)

```
# ✅ CORRECT project structure
digitized_filing/
├── accounts/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── validators.py
├── documents/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── upload_handlers.py
├── audit_logs/
├── departments/
└── filing_years/
```

---

### 9.3 React Frontend — Naming Standards

#### Components & Files
- Use **`PascalCase`** for all React component names and their files.
- Use **`kebab-case`** for non-component files (hooks, utilities, context, API files).
- Component files use `.jsx` extension; utility/hook files use `.js`.

```
# ✅ CORRECT file names
DocumentTable.jsx           # React component — PascalCase
LoginPage.jsx               # React page component — PascalCase
WelcomePage.jsx             # React page component — PascalCase
use-document-filters.js     # Custom hook — kebab-case
auth-context.jsx            # Context — kebab-case
axios-instance.js           # Utility — kebab-case
document-helpers.js         # Helper functions — kebab-case

# ❌ WRONG file names
documenttable.jsx           # no separator, hard to read
document_table.jsx          # snake_case — not React convention
loginpage.jsx               # all lowercase, unclear word boundary
DocumentHelpers.js          # PascalCase for non-component — wrong
```

#### Variables & State
- Use **`camelCase`** for all variables, state variables, props, and object keys.
- Boolean variables should use `is`, `has`, or `can` as a prefix.

```javascript
// ✅ CORRECT
const [documentList, setDocumentList]     = useState([]);
const [isLoading, setIsLoading]           = useState(false);
const [hasError, setHasError]             = useState(false);
const [selectedCategory, setSelectedCategory] = useState('');
const [filingYear, setFilingYear]         = useState('');
const currentUser = user.full_name;
const canUpload   = user.role === 'admin' || user.role === 'staff';

// ❌ WRONG
const [data, setData]   = useState([]);   // too vague — data what?
const [flag, setFlag]   = useState(false);// flag for what?
const [x, setX]         = useState('');  // single letter
const loading           = useState(false);// missing 'is' prefix for boolean
const DocumentList      = useState([]);   // PascalCase for variable — wrong
```

#### Functions & Event Handlers
- Use **`camelCase`** for all functions.
- Start with a **verb** that describes the action.
- Event handlers must be prefixed with `handle`.

```javascript
// ✅ CORRECT
const fetchDocuments    = async (filters) => { ... };
const uploadDocument    = async (file, category) => { ... };
const archiveDocument   = async (documentId) => { ... };
const handleFilterChange   = (key, value) => { ... };
const handleFormSubmit     = async (e) => { ... };
const handleCategorySelect = (value) => { ... };

// ❌ WRONG
const getdocs  = () => { ... };    // no separator, unclear
const DoUpload = () => { ... };    // PascalCase — reserved for components
const clicked  = () => { ... };    // past tense, not descriptive
const fn1      = () => { ... };    // meaningless name
const onChange = () => { ... };    // missing 'handle' prefix for event handler
```

#### Constants & Configuration
- Use **`SCREAMING_SNAKE_CASE`** for constants.
- Store environment variables in `.env` with `VITE_` prefix for Vite projects.

```javascript
// ✅ CORRECT constants
const MAX_FILE_SIZE_MB   = 20;
const ALLOWED_STATUSES   = ['not_sent', 'sent', 'received', 'archived'];
const DEFAULT_PAGE_SIZE  = 10;

// ✅ CORRECT environment variables in .env
VITE_API_URL=http://localhost:8000
VITE_APP_TITLE=Digitized Filing System

// Usage in code
const apiUrl = import.meta.env.VITE_API_URL;
```

#### React Component Structure
Components must follow this consistent internal order:

```javascript
// ✅ CORRECT component structure
export default function DocumentTable({ filters, onRowClick }) {
  // 1. Hooks first
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const { user } = useAuth();
  const tableRef = useRef(null);

  // 2. Effects
  useEffect(() => { ... }, [filters]);

  // 3. Handler functions
  const handleRowClick    = (doc) => { ... };
  const handlePageChange  = (page) => { ... };

  // 4. Render helpers (if needed)
  const renderStatusBadge = (status) => { ... };

  // 5. Return JSX last
  return ( <div>...</div> );
}
```

---

### 9.4 Shared Conventions — Both Django & React

| Rule | Description |
|------|-------------|
| **Be descriptive, not verbose** | `documentUploadedByUser` is too long. `uploadedDocument` is clear. `doc` is too short. |
| **No single-letter variables** | Except loop counters (`i`, `j`) in very short loops. Always prefer `document` over `d`. |
| **No abbreviations** | `usr` → `user`, `dept` → `department`, `doc` → `document`, `cat` → `category`. Exception: well-known acronyms like `id`, `url`, `api`, `nas`. |
| **No misleading names** | Don't name a list `documentData` if it's a single object. Don't use `temp` unless it's genuinely temporary. |
| **Consistent verbs** | Pick one verb per action and stick to it. Use `fetch` for API calls, `get` for local retrieval, `handle` for event handlers, `validate` for validation. |
| **No magic numbers** | Never use raw numbers in logic. Define them as named constants. `if (file.size > 20971520)` → `if (file.size > MAX_FILE_SIZE_BYTES)` |
| **Boolean naming** | Always prefix with `is_`, `has_`, `can_` in Python / `is`, `has`, `can` in JS. `active` → `is_active`, `error` → `has_error`. |

---

### 9.5 Document & NAS File Naming

Uploaded documents saved to the NAS must follow a consistent, readable file naming pattern to ensure files are traceable and never collide.

**NAS File Naming Format:**
```
{YYYY}_{category_slug}_{original_sanitized_filename}_{uuid_short}.pdf
```

**Examples:**
```
2025_memo_budget-approval-q1_a3f9b2.pdf
2025_report_academic-performance-summary_c81d4e.pdf
2024_letter_department-directive-nov_f20a91.pdf
```

**Rules:**
- Year prefix for instant year identification without opening the folder
- Category slug from the document's assigned category
- Original filename sanitized: lowercase, spaces replaced with hyphens, special characters removed
- Short UUID suffix (6 characters) to prevent filename collisions
- All lowercase, kebab-case separators within the filename segment
- Extension always `.pdf` for the primary format

**Django implementation — sanitize filename on upload:**
```python
import uuid
from django.utils.text import slugify

def generate_nas_filename(category_slug, original_filename, filing_year):
    name_without_ext = original_filename.rsplit('.', 1)[0]
    sanitized        = slugify(name_without_ext)          # lowercase + hyphens
    short_uuid       = str(uuid.uuid4()).replace('-', '')[:6]
    return f"{filing_year}_{category_slug}_{sanitized}_{short_uuid}.pdf"

# Example output: 2025_memo_budget-approval-q1_a3f9b2.pdf
```

---

### 9.6 Icon Standards — Lucide React (Required)

Since this project uses **ShadCN/UI**, the icon library is **Lucide React** — ShadCN's components are built with Lucide icons internally, and Lucide is already installed as a dependency when ShadCN is set up. Using any other icon library (Material Icons, FontAwesome, etc.) would break visual consistency since ShadCN's own components already render Lucide icons.

> **Rule:** Use **Lucide React** for all UI icons across every page. Emojis are only acceptable in non-functional, decorative text content (e.g., a welcome message body paragraph). Never use emojis as buttons, labels, status indicators, or navigation icons.

---

#### Why Lucide Over Material Icons

| | Lucide React | Material Icons (`@mui/icons-material`) |
|--|---|---|
| Already installed with ShadCN | ✅ Yes | ❌ No — extra install |
| Visual consistency with ShadCN components | ✅ Native | ⚠️ Mismatch in stroke vs filled style |
| Bundle size | ✅ Tree-shakable, lightweight | ⚠️ Heavier — pulls in MUI dependencies |
| Tailwind className support | ✅ Full support | ⚠️ Requires `sx` prop or extra config |
| Works with ShadCN `Button`, `DropdownMenu`, etc. | ✅ Seamless | ⚠️ Style conflicts |

---

#### Installation

Lucide is built with ES Modules, so it's completely tree-shakable. Each icon can be imported as a React component, which renders an inline SVG element. This way, only the icons that are imported into your project are included in the final bundle. The rest of the icons are tree-shaken away.

Even though ShadCN installs `lucide-react` automatically, **always verify it is present** in `package.json` before development starts. Install explicitly if missing:

```bash
# npm
npm install lucide-react

# yarn
yarn add lucide-react

# pnpm
pnpm add lucide-react

# bun
bun add lucide-react
```

> ✅ **Verify installation** — after installing, confirm the package is listed in `package.json` under `dependencies`:
> ```json
> {
>   "dependencies": {
>     "lucide-react": "^0.x.x"
>   }
> }
> ```

**Icon props accepted** — Lucide icons accept all standard SVG attributes as props, giving full flexibility for styling:

```javascript
import { Camera } from 'lucide-react';

// size and color via props
<Camera color="red" size={48} />

// OR — preferred for this project — via Tailwind className
<Camera className="w-4 h-4 text-[#00491E]" />
```

> ⚠️ **Never use `import * as icons from 'lucide-react'`** — this imports the entire library and significantly increases bundle size. Always import only the specific icons you need per component.

---

#### Usage Pattern

```javascript
// ✅ CORRECT — import only the icons you need (tree-shakable)
import {
  UploadCloud,
  Inbox,
  Send,
  Archive,
  Search,
  Filter,
  FileText,
  Folder,
  User,
  ShieldCheck,
  Building2,
  History,
  Bell,
  Eye,
  Download,
  LogOut,
  Settings,
  CircleCheck,
  CircleDashed,
  PackageCheck,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';

// Usage in JSX — pairs natively with ShadCN Button
import { Button } from '@/components/ui/button';

<Button className="flex items-center gap-2">
  <UploadCloud className="w-4 h-4" />
  Upload Document
</Button>
```

---

#### Standard Icon Map for This Project

Every feature area has a designated Lucide icon — use these consistently across **all pages**. Do not swap icons between features.

| Feature / Action | Lucide Component | Size Class |
|------------------|------------------|------------|
| Upload Document | `<UploadCloud />` | `w-4 h-4` |
| Inbox | `<Inbox />` | `w-4 h-4` |
| Sent Items | `<Send />` | `w-4 h-4` |
| Archived | `<Archive />` | `w-4 h-4` |
| Search | `<Search />` | `w-4 h-4` |
| Filter | `<Filter />` | `w-4 h-4` |
| Document / File | `<FileText />` | `w-4 h-4` |
| Folder / Category | `<Folder />` | `w-4 h-4` |
| User / Profile | `<User />` | `w-4 h-4` |
| Admin | `<ShieldCheck />` | `w-4 h-4` |
| Department | `<Building2 />` | `w-4 h-4` |
| Audit Log | `<History />` | `w-4 h-4` |
| Notification | `<Bell />` | `w-4 h-4` |
| View / Read-only | `<Eye />` | `w-4 h-4` |
| Download | `<Download />` | `w-4 h-4` |
| Logout | `<LogOut />` | `w-4 h-4` |
| Settings | `<Settings />` | `w-4 h-4` |
| Status: Not Sent | `<CircleDashed />` | `w-4 h-4` |
| Status: Sent | `<Send />` | `w-4 h-4` |
| Status: Received | `<Inbox />` | `w-4 h-4` |
| Status: Archived | `<PackageCheck />` | `w-4 h-4` |
| Error / Warning | `<AlertCircle />` | `w-4 h-4` |
| Success | `<CheckCircle2 />` | `w-4 h-4` |

---

#### Sizing Standards

Lucide icons are sized using **Tailwind width/height classes** — not a `fontSize` prop like Material Icons. Use these three sizes only and never set arbitrary pixel values.

| Context | Tailwind Class | Pixel Size | Use case |
|---------|----------------|------------|----------|
| Inline / Button | `w-4 h-4` | 16px | Inside buttons, table cells, badges, input fields |
| Navigation / Card | `w-5 h-5` | 20px | Sidebar nav items, card headers, dropdowns |
| Empty State / Header | `w-8 h-8` | 32px | Empty state illustrations, page-level headers |

```javascript
// ✅ CORRECT sizing
<Search className="w-4 h-4" />            // inside search input
<Inbox className="w-5 h-5" />             // sidebar nav item
<FileText className="w-8 h-8" />          // empty state — "No documents yet"

// ❌ WRONG — never use arbitrary inline styles
<Send style={{ width: '18px' }} />        // bypasses standard, hard to maintain
<Archive style={{ fontSize: '24px' }} />  // fontSize doesn't apply to Lucide
```

---

#### Color Standards

Icons use Tailwind color classes — consistent with brand colors and semantic meanings.

```javascript
// ✅ CORRECT — brand and semantic colors via Tailwind
<UploadCloud  className="w-4 h-4 text-[#00491E]" />   // brand green — primary actions
<Archive      className="w-4 h-4 text-gray-400" />     // muted — secondary/inactive
<AlertCircle  className="w-4 h-4 text-red-500" />      // semantic — errors
<CheckCircle2 className="w-4 h-4 text-green-600" />    // semantic — success
<Bell         className="w-4 h-4 text-[#FFC600]" />    // brand yellow — notifications

// Brand color reference for icons:
// text-[#00491E]  — primary actions, active nav, upload, main CTAs
// text-[#FFC600]  — accent, notifications, highlights
// text-gray-400   — inactive, muted, secondary icons
// text-red-500    — errors, destructive actions
// text-green-600  — success states, confirmed status
```

---

#### What NOT to Use

```javascript
// ❌ WRONG — emojis as functional UI icons
<button>📤 Upload</button>              // inconsistent across OS and browsers
<span>📥 Inbox (3)</span>               // not accessible, not scalable
<div>✅ Document received</div>         // renders differently per platform

// ❌ WRONG — mixing other icon libraries with Lucide
import UploadFileIcon from '@mui/icons-material/UploadFile';  // MUI — style mismatch with ShadCN
import { FaUpload }   from 'react-icons/fa';                  // FontAwesome — not consistent
import { BiInbox }    from 'react-icons/bi';                  // Boxicons — not consistent

// ✅ CORRECT — Lucide React only, everywhere
import { UploadCloud, Inbox } from 'lucide-react';
<UploadCloud className="w-4 h-4 text-[#00491E]" />
<Inbox className="w-5 h-5" />
```

> **One library. One style. All pages.** Lucide React is the single approved icon source for this project — it is already part of ShadCN, uses the same visual language as all ShadCN components, and works natively with Tailwind CSS classes.

---



## 10. Data Model Overview

Based on stakeholder consultation, the system is projected to have approximately **11 core entities**:

| Entity | Description |
|--------|-------------|
| **User** | Stores user credentials, role, and department assignment |
| **Department** | Organizational units that group users and documents |
| **Folder** | Hierarchical container for subfolders and documents using self-referencing `parent_id` |
| **Document** | File metadata, category, filing year, uploader, and storage path |
| **Delivery** | Routing records linking documents to recipients (Read-only enforced) |
| **Category** | Admin-managed document type classifications (Memo, Reports, etc.) |
| **FilingYear** | Year-based archive grouping for document organization and filtering |
| **AuditLog** | Timestamped records of all system events and user actions |
| **Notification** | In-app alerts sent to recipients when a document is routed to them |
| **UserSession** | Tracks active login sessions per user for security and audit purposes |
| **SystemSetting** | Admin-configurable system parameters (file size limits, retention policies, etc.) |

> Entity count and relationships are subject to refinement during the database design phase. Final count is currently projected at approximately 11 because folder hierarchy is modeled as a first-class entity.

### 10.1 Folder Hierarchy Data Model

The folder system must use a **self-referencing relational model**.

#### Minimal relational structure

**folders**
- `id` — Primary Key
- `name`
- `parent_id` — Nullable Foreign Key → `folders.id`
- `department_id` — Nullable Foreign Key → `departments.id`
- `created_by_id` — Foreign Key → `users.id`
- `created_at`
- `updated_at`

**documents**
- `id` — Primary Key
- `title`
- `file_path`
- `folder_id` — Foreign Key → `folders.id`
- `uploaded_by_id` — Foreign Key → `users.id`
- `category_id` — Foreign Key → `categories.id`
- `filing_year`
- `created_at`
- `updated_at`

#### Relationship summary
- One folder can have many child folders
- One folder can have many documents
- One document belongs to one folder
- Root folders have `parent_id = NULL`

#### Why this is preferred
This model is preferred over creating separate tables for “cabinet,” “compartment,” “subfolder,” and other fixed levels. A fixed-level design is rigid, harder to scale, and breaks once the organization wants another nesting level. A self-referencing folder table keeps the model simple and expandable.

#### Example simulation
```text
SDD (root)
├── Hanging Cabinet 1
│   └── Compartment 1 - HC1
│       ├── Human Resource Folder
│       └── Projects
├── Hanging Cabinet 2
└── Hanging Cabinet 3
```

#### SQL usage examples

**Get all root folders**
```sql
SELECT id, name
FROM folders
WHERE parent_id IS NULL
ORDER BY name;
```

**Get children of one folder**
```sql
SELECT id, name, parent_id
FROM folders
WHERE parent_id = 801
ORDER BY name;
```

**Get documents inside one folder**
```sql
SELECT id, title, file_path, folder_id
FROM documents
WHERE folder_id = 804
ORDER BY title;
```

**Example recursive breadcrumb query (MySQL 8+)**
```sql
WITH RECURSIVE folder_path AS (
    SELECT id, name, parent_id, CAST(name AS CHAR(1000)) AS full_path
    FROM folders
    WHERE id = 807

    UNION ALL

    SELECT f.id, f.name, f.parent_id,
           CONCAT(f.name, ' / ', fp.full_path)
    FROM folders f
    JOIN folder_path fp ON fp.parent_id = f.id
)
SELECT full_path
FROM folder_path
WHERE parent_id IS NULL;
```



Based on stakeholder consultation, the system is projected to have approximately **10 core entities**:

| Entity | Description |
|--------|-------------|
| **User** | Stores user credentials, role, and department assignment |
| **Department** | Organizational units that group users and documents |
| **Document** | File metadata, category, filing year, uploader, and storage path |
| **Delivery** | Routing records linking documents to recipients (Read-only enforced) |
| **Category** | Admin-managed document type classifications (Memo, Reports, etc.) |
| **FilingYear** | Year-based archive grouping for document organization and filtering |
| **AuditLog** | Timestamped records of all system events and user actions |
| **Notification** | In-app alerts sent to recipients when a document is routed to them |
| **UserSession** | Tracks active login sessions per user for security and audit purposes |
| **SystemSetting** | Admin-configurable system parameters (file size limits, retention policies, etc.) |

> Entity count and relationships are subject to refinement during the database design phase. Final count confirmed at approximately 10 based on stakeholder consultation.

---

## 11. Phase 2 Roadmap — Internet-Based Cloud Access

Based on stakeholder input, the primary Phase 2 priority is migrating from a LAN-only deployment to a secure, internet-based cloud-accessible platform.

### 10.1 Phase 2 Key Objectives
- Host the application on a cloud server (e.g., AWS, Azure, or a private VPS).
- Implement HTTPS/TLS encryption for all traffic.
- Add multi-factor authentication (MFA) for remote login security.
- Enable remote access for authorized users from outside the office.
- Maintain all Phase 1 features with cloud-scale reliability.

### 10.2 Phase 2 Technical Considerations
- Server migration from internal LAN to cloud hosting provider.
- Storage migration: move from local NAS to cloud object storage (e.g., AWS S3).
- DNS configuration and SSL certificate management.
- VPN or IP whitelisting as an optional access restriction layer.
- Data migration plan from Phase 1 MySQL instance.

---

## 12. Security Risks & Validation Standards

This section defines all security risks identified for the Digitized Filing System and the required mitigation for each — organized by category based on established security standards and Django ORM best practices. Every item is a **required implementation standard**, not optional.

---

### 11.1 Secrets & Configuration

| Risk | Mitigation |
|------|------------|
| Hardcoded secrets, DB credentials, or JWT config in codebase | Use `.env` file with `python-decouple`. Never hardcode `SECRET_KEY`, DB passwords, or API keys. |
| `.env` file committed to Git | Add `.env` to `.gitignore` immediately. Provide `.env.example` with placeholder values for the team. |
| Debug mode enabled in production | Set `DEBUG = False` via environment variable. Debug mode exposes stack traces and internal config. |
| CORS too permissive | Restrict `CORS_ALLOWED_ORIGINS` to exact LAN IPs only — never use `CORS_ALLOW_ALL_ORIGINS = True`. |
| Default or example credentials still present | Remove all default credentials. Enforce strong passwords on all accounts at creation. |
| Dependencies with known vulnerabilities | Run `pip audit` before deployment. Pin package versions in `requirements.txt`. |

**Implementation:**
```python
# settings.py — load all secrets from environment
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG      = config('DEBUG', cast=bool, default=False)

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.mysql',
        'NAME':     config('DB_NAME'),
        'USER':     config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST':     config('DB_HOST', default='localhost'),
        'PORT':     config('DB_PORT', default='3306'),
    }
}

CORS_ALLOWED_ORIGINS = [
    "http://192.168.1.100:5173",   # Exact LAN IP — no wildcards
]
```

```bash
# .env — never commit this file
SECRET_KEY=your-very-secret-key-here
DEBUG=False
DB_NAME=digitized_filing_db
DB_USER=db_user
DB_PASSWORD=db_password
DB_HOST=localhost
DB_PORT=3306
```

---

### 11.2 Access & API Security

| Risk | Mitigation |
|------|------------|
| Pages or routes accessible without authentication | Every Django view except `/api/auth/login/` requires `IsAuthenticated` permission class. |
| Users accessing other users' data by changing a document ID in the URL | Always filter querysets by `request.user` — never trust URL parameters alone for authorization. |
| Tokens stored insecurely on the client | JWT access token in `localStorage` (short-lived, 8hrs). Refresh token blacklisted on logout. |
| Login response revealing whether an account exists | Return a single generic error for both wrong email and wrong password — prevents account enumeration. |
| Endpoints missing rate limiting | Apply `django-ratelimit` on `/api/auth/login/` — max 5 attempts per minute per IP. |
| Error responses exposing internal system details | Disable Django debug pages in production. DRF custom exception handler returns safe messages only. |
| Endpoints returning more data than needed | Serializers must use explicit `fields` list — `fields = '__all__'` is banned across the project. |
| Admin routes protected only by hiding the URL | Role-based permission classes enforced on every admin endpoint — URL obscurity is not security. |
| Sensitive actions with no confirmation step | Document archiving and user deactivation must require an explicit confirmation before executing. |

**Object-Level Permission — Never Trust URL ID Alone:**
```python
# ✅ CORRECT — always scope queryset to the requesting user
class DocumentDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(
            Q(uploader=self.request.user) |
            Q(deliveries__recipient=self.request.user)
        ).distinct()

# ❌ WRONG — any authenticated user can access any document by guessing the ID
def get_document(request, pk):
    doc = Document.objects.get(pk=pk)
    return Response(doc)
```

**Generic Login Error — Prevent Account Enumeration:**
```python
# ✅ CORRECT — same message regardless of which field is wrong
def validate(self, data):
    user = authenticate(username=data['email'], password=data['password'])
    if not user or not user.is_active:
        raise serializers.ValidationError(
            "Invalid credentials. Please check your email and password."
        )
    return data
```

**Rate Limiting on Login Endpoint:**
```python
# pip install django-ratelimit
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    ...
```

---

### 11.3 User Input & Django ORM Security

| Risk | Mitigation |
|------|------------|
| Unsanitized input reaching database queries | Always use Django ORM — it generates parameterized queries internally, preventing SQL injection. |
| Raw SQL with string formatting or f-strings | Strictly prohibited. If raw SQL is ever necessary, use bound parameters only — never f-strings. |
| File uploads accepted without type or size validation | Validate MIME type server-side using `python-magic`. Validate file size before saving to NAS. |
| XSS — user text executing code in other users' browsers | DRF serializers sanitize input. React renders text safely by default — never use `dangerouslySetInnerHTML`. |

**Django ORM vs Raw SQL — Critical Rule:**

> ⚠️ **Always use Django ORM for all database queries in this project. Raw SQL with user-supplied input is strictly prohibited.**

Django ORM generates **parameterized SQL** under the hood — `filter(title__icontains=query)` becomes `WHERE title LIKE %s` with the value safely bound separately, not interpolated into the string. This makes ORM the only approved query method for this project.

```python
# ✅ CORRECT — Django ORM (parameterized, SQL injection safe)
documents = Document.objects.filter(
    category=category,
    filing_year=year,
    uploader__department=request.user.department
)

# ✅ CORRECT — ORM with search input (safe)
results = Document.objects.filter(title__icontains=search_query)

# ✅ CORRECT — ORM with multiple filters and ordering
Document.objects.filter(
    status='sent',
    deliveries__recipient=request.user
).select_related('uploader', 'category').order_by('-created_at')

# ❌ WRONG — raw SQL with f-string (SQL injection vulnerability)
Document.objects.raw(
    f"SELECT * FROM documents WHERE title LIKE '%{search_query}%'"
)

# ❌ WRONG — cursor with string formatting (never do this)
cursor.execute(f"SELECT * FROM documents WHERE category = '{category}'")
```

**If raw SQL is ever absolutely necessary (rare edge cases only):**
```python
# ✅ Only acceptable raw SQL pattern — hardcoded query, bound parameters
Document.objects.raw(
    "SELECT * FROM documents_document WHERE filing_year = %s",
    [year]   # value bound separately — never concatenated
)
```

**Server-Side File Upload Validation:**
```python
# pip install python-magic
import magic

ALLOWED_MIME_TYPES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
]
MAX_FILE_SIZE_MB = 20

def validate_uploaded_file(file):
    # Size check
    if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"File must not exceed {MAX_FILE_SIZE_MB}MB.")

    # MIME type check — extensions can be faked, always check actual content
    mime = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)
    if mime not in ALLOWED_MIME_TYPES:
        raise ValidationError(f"Unsupported file type. Only PDF and DOCX are allowed.")
```

---

### 11.4 React Frontend Validation

Frontend validation improves UX but is **never a substitute for backend validation**. All inputs must be validated on both sides — the backend is the true security boundary.

**Form Validation Before API Call:**
```javascript
const validateLoginForm = (form) => {
  const errors = {};
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (!form.email)                        errors.email    = 'Email is required.';
  else if (!emailRegex.test(form.email))  errors.email    = 'Enter a valid email address.';
  if (!form.password)                     errors.password = 'Password is required.';
  else if (form.password.length < 8)      errors.password = 'Password must be at least 8 characters.';

  return errors;
};
```

**Safe Error Handling in Axios — Never Expose Internal Details:**
```javascript
// ✅ CORRECT — user-friendly message only, no stack traces
try {
  const user = await login(form.email, form.password);
} catch (err) {
  const msg = err.response?.data?.non_field_errors?.[0];
  setError(msg || 'Login failed. Please try again.');
}
```

**Role Enforcement in Protected Routes:**
```javascript
// ✅ Always check both authentication AND role
export default function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingSpinner />;
  if (!user)   return <Navigate to="/login" replace />;
  if (allowedRoles && !allowedRoles.includes(user.role))
               return <Navigate to="/unauthorized" replace />;
  return children;
}

// ⚠️ Hiding buttons or menu items is UX only — the API must also enforce roles
```

---

### 11.5 Security Implementation Checklist

#### Secrets & Config
- [ ] All credentials loaded from `.env` via `python-decouple` — nothing hardcoded
- [ ] `.env` added to `.gitignore` — confirmed not committed
- [ ] `DEBUG = False` confirmed in production environment
- [ ] `CORS_ALLOWED_ORIGINS` restricted to exact LAN IPs — no wildcards
- [ ] `pip audit` run and passing before deployment

#### Access & API
- [ ] All endpoints except `/api/auth/login/` require `IsAuthenticated`
- [ ] All querysets filtered by `request.user` — URL IDs never trusted alone
- [ ] Login returns single generic error — does not reveal if email exists
- [ ] Rate limiting active on `/api/auth/login/` — 5 attempts/min per IP
- [ ] All serializers use explicit `fields` list — `fields = '__all__'` not used anywhere
- [ ] Role-based permissions enforced on all admin endpoints
- [ ] Sensitive actions (archive, deactivate) require confirmation step

#### User Input & ORM
- [ ] All database queries use Django ORM — no raw SQL with user input anywhere
- [ ] File MIME type validated server-side with `python-magic`
- [ ] File size validated server-side before NAS write
- [ ] No `dangerouslySetInnerHTML` used in any React component

#### React Frontend
- [ ] Email and password validated client-side before submission
- [ ] Axios error handler shows only safe user-friendly messages
- [ ] `ProtectedRoute` enforces both authentication and role
- [ ] API base URL stored in `.env` — not hardcoded in Axios config

---

## 13. Success Metrics

- Zero document misplacement incidents within 30 days of go-live.
- Document retrieval time reduced to under 2 seconds.
- 100% of targeted departments onboarded within 3 months.
- Audit log coverage of all upload, access, and routing events.
- Positive feedback from at least 80% of users in post-launch survey.
- System adoption confirmed across all participating departments.

---

## 14. Risks & Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| User resistance to adoption | Provide department orientation and short user training sessions |
| Storage overload from large file uploads | Implement configurable file size limits and storage monitoring |
| Unauthorized access to documents | Enforce strict role-based access control and log all access attempts |
| Server or hardware failure | Implement daily automated backups and a documented recovery plan |
| Slow LAN performance under load | Optimize queries, paginate results, and test with simulated 100-user load |
| Phase 2 cloud migration complexity | Plan migration in parallel with Phase 1 stabilization; test in staging |

---

## 15. Deployment Timeline — 1 to 3 Months

| Week | Milestone |
|------|-----------|
| **Week 1** | Requirements finalization and team alignment |
| **Week 2** | Authentication module, roles, and department setup |
| **Week 3** | Document upload, storage, and categorization |
| **Week 4** | Document routing and permission enforcement |
| **Week 5** | Search, filtering, status tracking, and audit logging |
| **Week 6** | Integration testing, bug fixing, and LAN deployment |
| **Week 7–8** | User orientation, pilot run, and feedback collection |
| **Week 9–12** | Stabilization, minor enhancements, and Phase 2 planning |

---

## 16. Conclusion

The Digitized Filing System provides a structured, secure, and efficient approach to managing approved scanned documents within a LAN-based desktop environment. Designed for a medium-sized organization of 21 to 100 users, it enhances accountability, improves document traceability, and standardizes digital filing across all departments.

With a short-term deployment window of 1 to 3 months for Phase 1, and a clear Phase 2 roadmap targeting internet-based cloud access, the system is positioned to grow with the organization's evolving needs.

---

---

> ⚠️ **DRAFT — Version 2.6** | This document is pending final review and approval before it is considered finalized.

*Confidential — Internal Use Only | Version 2.6 DRAFT | March 2026*
