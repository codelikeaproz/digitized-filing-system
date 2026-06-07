# DigiFile — VPAA Presentation Guide

**Digitized Filing System (DFS)**  
Use this guide during your live demo. English script is for formal delivery; Taglish notes are optional shortcuts if the VPAA prefers a conversational tone.

**Suggested demo time:** 10–15 minutes  
**Demo account:** Admin (e.g. Boy Admin) — shows all modules

---

## Table of Contents

1. [Opening](#1-opening)
2. [Who Uses the System](#2-who-uses-the-system)
3. [Module-by-Module Script](#3-module-by-module-script)
4. [Technical Notes (Q&A)](#4-technical-notes-for-vpaa-questions)
5. [Suggested Demo Flow](#5-suggested-demo-flow-1015-minutes)
6. [Likely VPAA Questions](#6-likely-vpaa-questions)
7. [Closing Statement](#7-closing-statement)

---

## 1. Opening

### What to say (English)

> Good [morning/afternoon], [Name]. Thank you for your time.
>
> Today I will show you **DigiFile** — our **Digitized Filing System**. Its purpose is simple: replace scattered paper files with one secure, searchable digital filing system for the institution.
>
> With DigiFile, offices can upload PDF documents, organize them by folder and office unit, search quickly, and track who did what. Storage is controlled so we do not run out of server space unexpectedly.
>
> I will walk through each module briefly, then answer any questions — including where files are actually stored on the server.

### Taglish summary

> Good [morning/afternoon], [Name]. Ipapakita ko po ang **DigiFile** — yung digitized filing system natin. Instead na naka-scatter ang paper files, nandito na lahat sa isang secure at searchable system. Makikita niyo po kung paano mag-upload, mag-organize, at ma-monitor ang storage per office unit.

---

## 2. Who Uses the System

Three user roles control what each person can see and do.

| Role | Plain name | What they can access |
|------|------------|----------------------|
| **Admin** | System administrator (IT / records office) | All modules — Dashboard, Documents, Office Units, User Management, Audit Logs, Recycle Bin, Settings, Backup Management |
| **Dept Head** | College dean / department head | Dashboard, Documents, User Management (Staff only in their unit), Recycle Bin, Settings |
| **Staff** | Office staff | Dashboard, Documents, Settings — upload and manage files; cannot delete documents |

### Taglish summary

> Tatlong roles lang po: **Admin** — full access; **Head** — manage staff sa kanilang office unit; **Staff** — upload at manage documents lang, hindi pwede mag-delete.

---

## 3. Module-by-Module Script

Each section has:
- **What to say** — speaking script
- **What you see** — short label for each display on screen
- **Taglish summary** — optional quick version

---

### 3.1 Dashboard

**Route:** `/` (first page after login)  
**Who sees it:** Admin, Dept Head, Staff (data scoped by role and office unit)

#### What to say (English)

> This is the **Dashboard** — the overview page. At a glance, we see how many documents are filed, how many files are uploaded, and how storage is being used across the institution.
>
> The admin can filter by office unit to focus on one college or department. The storage chart shows used space versus remaining space, and the bar chart compares each office unit's allocated quota against actual file usage.
>
> The notification bell in the header alerts us when storage is getting full.

#### What you see on screen

| Display | Short explanation |
|---------|-------------------|
| **Total Documents** | Count of all document records in the system |
| **Uploaded Files** | Count of files actually uploaded (PDFs) |
| **Total Office Units** | Number of configured office units (Admin view) |
| **Total Users** | Number of registered user accounts (Admin view) |
| **Office Unit filter** | Dropdown to view stats for all units or one unit |
| **Storage Utilization chart** | Donut chart — used vs remaining file storage |
| **Used Storage** | Total megabytes/gigabytes of uploaded files |
| **Remaining Storage (files)** | File space left based on actual uploads |
| **System Storage Limit** | Total server storage capacity (e.g. 100 GB) |
| **Total Top-Level Allocated** | Storage already assigned to root office units |
| **System Allocation Remaining** | Unassigned quota still available to give out |
| **Percentage Used** | How full the system is (by file usage) |
| **Office Unit Storage Comparison** | Bar chart — quota vs used per office unit |
| **Notification bell** | Storage alerts at 80%, 90%, 95%, 100% usage |

#### Taglish summary

> Dito po makikita agad kung ilan ang documents, files, at users. May chart din para sa storage — kung gaano na karaming space ang nagamit at kung magkano pa ang natitira per office unit.

---

### 3.2 Documents

**Route:** `/documents`  
**Who sees it:** All roles (files scoped by office unit)

#### What to say (English)

> **Documents** is the core of the system — this is where staff file their PDFs digitally.
>
> On the left is the folder tree organized by office unit. On the right is the document list. Users can upload PDFs, search by title or keywords, filter by category and date, preview files without printing, and download when needed.
>
> The **Document Assistant** button lets users ask questions in plain language to find files faster — for example, "Show me invoices from March."

#### What you see on screen

| Display | Short explanation |
|---------|-------------------|
| **Folder tree (left panel)** | Office units and folders — click to browse |
| **Breadcrumb trail** | Current location path (Home → folder → subfolder) |
| **Category filter** | Filter documents by document category |
| **Date range filter** | Filter by filing or upload date |
| **Upload button** | Add a new PDF (disabled when quota is full) |
| **Search bar** | Search by title, code, description, keywords |
| **Document table — Title** | Document name |
| **Document table — Requisitioner** | Person who requested the document |
| **Document table — Category** | Document type/category |
| **Document table — Location** | Folder path where file is stored |
| **Document table — Date** | Filing or upload date |
| **Document table — Status** | Active or other document status |
| **Document table — Actions** | View, Download, Rename, Edit, Delete |
| **PDF preview modal** | View PDF inside the browser |
| **Document Assistant** | AI helper to search documents by question |

#### Taglish summary

> Dito po ang main filing — upload ng PDF, organize sa folders, search, at preview without printing. May AI assistant din para mabilis hanapin ang files.

---

### 3.3 Office Units

**Route:** `/org-units`  
**Who sees it:** Admin only

#### What to say (English)

> **Office Units** is where the admin sets up the organizational structure — colleges, departments, and offices — and assigns storage quotas to each one.
>
> Think of it like a budget: the system has a total storage limit, say 100 GB. The admin gives each top-level unit an envelope — for example, CISC gets 15 GB. From that 15 GB, the admin can assign portions to child units like SDD or Registrar.
>
> Important: child quotas come from the parent's envelope. They are not extra storage on top. So if CISC has 15 GB and gives 11 GB to its children, 4 GB remains in CISC's pool for future assignments or its own files.
>
> Leaf units — those with no sub-units — show **0 MB** in To Children and their full envelope in Pool Available.

#### What you see on screen

| Display | Short explanation |
|---------|-------------------|
| **Name** | Office unit name (tree icon shows hierarchy) |
| **Type** | Unit type — College, Department, Office, etc. |
| **Envelope** | Total storage assigned to this unit |
| **To Children** | Storage already given to direct sub-units |
| **Pool Available** | Storage still assignable within this unit's envelope |
| **Used (files)** | Actual file storage consumed by uploads |
| **File Space Left** | Envelope minus file usage — room for more uploads |
| **Hierarchy (Parent)** | Parent unit name, or "None (Root)" for top-level |
| **Actions** | Edit or delete office unit |
| **Add Office Unit** | Create a new unit with quota and parent |
| **Organization Types** | Manage types like College, Department, Office |
| **Table footnote** | Explains envelope vs pool vs file space left |

**Example (from live data):**

| Unit | Envelope | To Children | Pool Available |
|------|----------|-------------|----------------|
| CISC (parent) | 15 GB | 11 GB | 4 GB |
| SDD (child) | 5 GB from CISC | 0 MB | 5 GB |

#### Taglish summary

> Dito po ini-set ang structure ng offices at kung magkano ang storage quota nila. Parang budget — may total limit ang system, tapos hati-hati per college/department. Yung child units, galing sa envelope ng parent — hindi additional storage.

---

### 3.4 User Management

**Route:** `/users`  
**Who sees it:** Admin (all users); Dept Head (Staff in their unit only)

#### What to say (English)

> **User Management** controls who can log in and what they can do.
>
> The admin creates accounts for all roles. A department head can add and manage staff within their office unit only. Each new user receives an activation email to set their password before first login.
>
> The role legend at the top explains the difference between Admin, Head, and Staff at a glance.

#### What you see on screen

| Display | Short explanation |
|---------|-------------------|
| **Role Permission Legend** | Summary of Admin, Head, Staff capabilities |
| **Search / filters** | Find users by name, role, or office unit |
| **Users table — Name** | User's full name |
| **Users table — Email** | Login email address |
| **Users table — Role** | Admin, Head, or Staff |
| **Users table — Office Unit** | Unit the user belongs to |
| **Users table — Status** | Active, pending activation, inactive |
| **Users table — Date Joined** | When account was created |
| **Add User** | Create a new account |
| **Actions menu** | Edit, activate/deactivate, resend email, delete |

#### Taglish summary

> Dito po nire-register ang users at sineset ang role nila. Admin lang ang full access; Head, staff sa unit nila lang; Staff, upload at manage documents lang.

---

### 3.5 Audit Logs

**Route:** `/audit-logs`  
**Who sees it:** Admin only

#### What to say (English)

> **Audit Logs** is our accountability trail. Every important action is recorded — who logged in, who uploaded a file, who edited or deleted a document, who changed a user account.
>
> The analytics charts show upload, delete, and edit activity per office unit. Admins can filter by date, role, or action type, and export everything to Excel for reporting.

#### What you see on screen

| Display | Short explanation |
|---------|-------------------|
| **Search bar** | Search by user name or action text |
| **Action filter** | Filter by action type (Upload, Login, Delete, etc.) |
| **Role filter** | Filter by Admin, Head, or Staff |
| **Office Unit filter** | Filter by office unit |
| **Date range filter** | Filter logs by date |
| **Export Excel** | Download audit log as spreadsheet |
| **Upload Count chart** | Uploads per office unit |
| **Deleted Files chart** | Deletions per office unit |
| **Edited Files chart** | Edits per office unit |
| **Logs table — Timestamp** | When the action happened |
| **Logs table — Name** | User who performed the action |
| **Logs table — Role** | User's role at time of action |
| **Logs table — Office Unit** | Related office unit |
| **Logs table — Action** | What was done (color-coded badge) |
| **Logs table — Details** | Extra information about the action |

#### Taglish summary

> Dito po recorded lahat — sino nag-upload, nag-delete, nag-login. May charts at Excel export din para sa reporting at compliance.

---

### 3.6 Recycle Bin

**Route:** `/recycle-bin`  
**Who sees it:** Admin, Dept Head

#### What to say (English)

> When someone deletes a document or folder, it goes to the **Recycle Bin** first — it is not gone immediately.
>
> Authorized users can restore items if deleted by mistake, or permanently delete them when they are sure. This gives a safety net before files are removed for good.

#### What you see on screen

| Display | Short explanation |
|---------|-------------------|
| **Type filter** | All Items, Documents Only, or Folders Only |
| **Refresh button** | Reload the deleted items list |
| **Table — Type** | Document or Folder |
| **Table — File Name** | Name of deleted item |
| **Table — Office Unit** | Which unit it belonged to |
| **Table — Deleted By** | User who deleted it |
| **Table — Role** | Role of the user who deleted |
| **Table — Date Deleted** | When it was deleted |
| **Restore** | Bring the item back |
| **Permanent Delete** | Remove forever (also removes file from server) |

#### Taglish summary

> Pag na-delete, pumupunta muna sa Recycle Bin — pwede i-restore kung mistake, or permanent delete kung sure na.

---

### 3.7 Settings

**Route:** `/settings`  
**Who sees it:** All roles (System tab: Admin only)

#### What to say (English)

> **Settings** is where users manage their own profile and password. Admins also set system-wide limits here — the maximum size of a single upload and the total storage capacity for the entire institution.

#### What you see on screen

| Display | Short explanation |
|---------|-------------------|
| **Profile tab** | Name, suffix, avatar, read-only email and employee number |
| **Security tab** | Change password (requires re-login after) |
| **System tab (Admin)** | Max upload size per file (MB) |
| **System tab (Admin)** | System-wide storage quota preset |
| **Minimum allowed quota** | Cannot set quota below current file usage or top-level Office Unit allocations |

#### Taglish summary

> Dito po ang profile at password ng user. Sa System tab naman, si Admin ang nagse-set ng upload limit at total storage ng buong system — hindi pwedeng ibaba ang quota kaysa sa nagamit na storage o sa naka-allocate na sa offices.

---

### 3.8 Backup Management

**Route:** `/backup` (under Administration in sidebar)  
**Who sees it:** Admin only

#### What to say (English)

> **Backup Management** lets the admin download two separate backup files.
>
> The **Database Backup** is the index — all records, users, folder structure, audit logs, and file references. The **Media Files Backup** is a ZIP of the actual uploaded PDFs and profile pictures.
>
> Both are needed for full recovery. If we only have one, we either have the list without the files, or the files without knowing where they belong.

#### What you see on screen

| Display | Short explanation |
|---------|-------------------|
| **Database Backup card** | Download `.sql` file — all system records |
| **Download Database Backup** | Button to save database snapshot |
| **Media Files Backup card** | Download `.zip` — all uploaded PDFs and images |
| **Download Media Backup** | Button to save media folder as ZIP |

#### Taglish summary

> May dalawang backup: database (records/index) at media (actual PDF files). Kailangan pareho para full recovery.

---

### 3.9 Login and Assistants

**Routes:** `/login`, `/forgot-password`, `/set-password/:token`

#### What to say (English)

> Before users can access the system, they log in with email and password. New users receive an activation link to set their password on first use.
>
> On the login page, the **DFS Assistant** answers general questions about how the system works. After login, on the Documents page, the **Document Assistant** helps search actual files — but only what the user is allowed to see.

#### What you see on screen

| Display | Short explanation |
|---------|-------------------|
| **Login form** | Email and password fields |
| **Forgot Password link** | Request password reset email |
| **DFS Assistant (login page)** | General help — no file access |
| **Document Assistant (Documents page)** | Search documents by natural language |

#### Taglish summary

> May login muna, tapos activation email para sa bagong users. May assistant din — general help sa login page, document search naman pag naka-login na.

---

## 4. Technical Notes (for VPAA Questions)

Plain-language answers for common technical questions. Use the **filing cabinet + index card** analogy when explaining storage.

---

### 4.1 Why files are in the `media` folder, not the database

**What to say (English)**

> When you upload a PDF, the system saves two things in two different places.
>
> **In the database (MySQL):** the index card — title, document code, folder location, who uploaded it, file size, searchable text, and audit records. This is small and fast to search.
>
> **In the media folder (server disk):** the actual PDF file — the bytes you would open and read. Files are stored under paths like `media/documents/2026/06/07/Report.pdf`.
>
> We do **not** put PDF files inside the database tables. If we did, the database would become very large, slow to back up, and slow for everyday searches. This is standard practice for document management systems — the database is the catalog; the media folder is the filing cabinet.

**Analogy**

| Part | Real-world equivalent | What it holds |
|------|----------------------|---------------|
| Database | Index card / ledger | Titles, codes, locations, users, logs |
| Media folder | Filing cabinet | Actual PDF files and profile pictures |

**Taglish summary**

> Yung database, parang index card lang — title, location, sino nag-upload. Yung actual PDF, nasa **media folder** sa server disk. Hindi namin nilalagay ang file sa database kasi mabibigat at mabagal yun. Standard po ito sa document systems.

---

### 4.2 Storage model (three layers)

**What to say (English)**

> Storage is controlled at three levels:
>
> 1. **System-wide limit** — total capacity for the whole institution (e.g. 100 GB on the server).
> 2. **Office Unit envelope** — how much each college or department is allowed (e.g. CISC 15 GB).
> 3. **Child allocation** — sub-units draw from their parent's envelope (e.g. SDD 5 GB from CISC). This does not add extra system storage — it subdivides the parent's share.
>
> Uploads are blocked when either the system limit or the office unit's file space is exceeded. Admins receive notifications when usage reaches 80%, 90%, 95%, and 100%.

**Taglish summary**

> Tatlong level: total system limit, envelope per office unit, tapos hati sa child units galing sa parent — hindi additional storage yung sa children.

---

### 4.3 Where data lives on the server (Docker)

**What to say (English)**

> In our server setup, data is stored in two persistent volumes that survive restarts:
>
> - **Database volume** — all records and metadata (MySQL).
> - **Media volume** — all uploaded PDFs and profile pictures.
>
> When we update the application code, uploaded files are not deleted. They stay on the media volume until an admin permanently deletes them or restores from backup.

**Taglish summary**

> Parehong naka-persist ang database at media folder kahit i-restart ang server. Hindi mawawala ang uploads pag nag-update ng app code.

---

### 4.4 Backup and recovery

**What to say (English)**

> Admins can download two backup files on demand:
>
> 1. **Database backup** (`.sql`) — all records, users, structure, audit logs.
> 2. **Media backup** (`.zip`) — all uploaded files.
>
> Full recovery requires both. Restoring is currently a manual IT procedure — import the SQL file into the database and replace the media folder contents with the ZIP contents.

**Taglish summary**

> Manual backup po — download database at media separately. Pareho kailangan para ma-restore lahat. Manual pa ang restore step ng IT.

---

### 4.5 Security highlights

| Feature | What it means |
|---------|---------------|
| Login required | No access without valid account |
| Role-based access | Admin, Head, Staff see different modules and data |
| Office unit scoping | Users see documents for their unit (and subtree for heads) |
| 10-minute idle logout | Session ends after inactivity |
| Soft delete + Recycle Bin | Deleted files can be recovered before permanent removal |
| Audit logs | Every major action is recorded with user and timestamp |
| Storage alerts | Admin notified before storage runs out |

**Taglish summary**

> May login, roles, auto-logout after 10 minutes, audit trail, at storage alerts para secure at accountable ang system.

---

## 5. Suggested Demo Flow (10–15 minutes)

Follow this order for a smooth presentation:

| Step | Action | Time |
|------|--------|------|
| 1 | Login as Admin | ~30 sec |
| 2 | **Dashboard** — show stat cards, filter "All Office Units", explain Storage Utilization chart | ~2 min |
| 3 | Point to **Office Unit Storage Comparison** chart | ~1 min |
| 4 | **Office Units** — show CISC hierarchy (Envelope, To Children, Pool Available, SDD as leaf) | ~2 min |
| 5 | **Documents** — browse folder tree, show one document preview, mention search and upload | ~2 min |
| 6 | **User Management** — show Role Permission Legend | ~1 min |
| 7 | **Audit Logs** — show one log entry, mention Excel export | ~1 min |
| 8 | **Recycle Bin** — explain restore vs permanent delete | ~30 sec |
| 9 | **Settings → System** — show system quota | ~30 sec |
| 10 | **Backup Management** — show both download cards | ~1 min |
| 11 | Click **notification bell** — mention storage alerts | ~30 sec |
| 12 | **Closing statement** (Section 7) | ~1 min |

---

## 6. Likely VPAA Questions

| Question | Short answer |
|----------|--------------|
| Can departments see each other's files? | No — access is limited by office unit and role. Staff see their unit; heads see their subtree; admin sees all. |
| What happens when storage is full? | New uploads are blocked. Admin gets notifications. Admin can increase system quota or reallocate office unit envelopes. |
| Is this secure? | Yes — login required, role-based access, audit trail, auto-logout after 10 minutes of inactivity. |
| Where are files physically stored? | On the server's **media folder** (disk storage), not inside database tables. The database only stores the file reference and metadata. |
| Can we recover deleted files? | Yes — first through the Recycle Bin (restore). If permanently deleted, only from backup (database + media ZIP). |
| Does child storage add to the parent? | No — child quotas come from the parent's envelope. CISC 15 GB with 11 GB to children leaves 4 GB pool at CISC level. |
| Can we export audit records? | Yes — Audit Logs page has Export Excel. |
| Who manages office structure and quotas? | Admin only, through Office Units and Settings → System. |

---

## 7. Closing Statement

### What to say (English)

> To summarize: **DigiFile** gives us one place to store, search, and manage institutional documents digitally. Each office unit has a clear storage allocation. Every action is logged for accountability. Files are stored safely on server disk, with the database serving as a fast searchable index.
>
> We are ready for your feedback and for phased rollout to additional offices when approved. Thank you again for your time.

### Taglish summary

> Yan po ang DigiFile — isang system para sa digital filing, may storage control per office, audit trail, at secure file storage sa media folder. Handa na po kami sa feedback niyo at sa rollout pag na-approve. Salamat po ulit.

---

## For Developers

Technical API and architecture details: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md), [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md), [FRONTEND_ROUTES.md](./FRONTEND_ROUTES.md)
