# Alpha Test Checklist

Manual testing guide for **Digitized Filing System (DFS)** alpha sign-off.

> **Related:** [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) · [CHATBOT_CAPABILITIES.md](../CHATBOT_CAPABILITIES.md)

---

## Setup

Use three accounts: **Admin**, **Dept Head**, and **Staff** (each with a valid Org Unit). Mark `[x]` when pass; note bugs inline.

| Role | Access |
|------|--------|
| Public | Login page + public assistant |
| Staff | Dashboard, Documents, Settings |
| Dept Head | + Requisitioners Directory (read-only), Users (Staff in org subtree), Recycle Bin |
| Admin | + Org Units, Audit Logs, Backup Management, Requisitioners Directory (full CRUD) |

**Sign-off:** Tester __________ · Date __________ · Pass / Fail __________

---

## 1. Authentication

| Test case | Role | Done |
|-----------|------|------|
| Login, logout, session refresh, protected route redirect | All | [ ] |
| Login / forgot / reset hero shows CMU tagline (not VPAA-only text) | Public | [ ] |
| Forgot / reset password flow works | All | [ ] |
| New user activation via `/set-password/...` | Admin-created | [ ] |
| Auto-logout after 10 min idle | All | [ ] |

---

## 2. Dashboard

| Test case | Role | Done |
|-----------|------|------|
| Stats load; summary cards show **Documents** and **G Drive Files** | All | [ ] |
| Dashboard refetches when returning to tab / window focus | All | [ ] |
| Admin-only cards (Org Units, Users) visible to Admin only | Admin | [ ] |
| Global view shows System Storage Limit, Top-Level Allocated, and System Allocation Remaining | Admin | [ ] |
| Low file usage shows `< 0.1%` and visible donut slice (not stuck at 0.0%) | Admin | [ ] |
| Admin filtering to parent Office Unit includes child documents and subtree usage | Admin | [ ] |
| Admin filtering to parent shows comparison chart with child units | Admin | [ ] |
| Office Unit Storage Comparison footer shows total used and total quota | Admin | [ ] |
| Parent Dept Head sees subtree folder tree (assigned unit + descendants) | Dept Head | [ ] |
| Parent Dept Head dashboard: 15 GB envelope (not parent + child quota sum); aggregates docs across subtree | Dept Head | [ ] |
| Parent Dept Head comparison chart lists child units; subtitle notes child inclusion when applicable | Dept Head | [ ] |
| Staff at parent unit: dashboard shows assigned unit only; no subtree aggregation or comparison chart | Staff | [ ] |
| Child Dept Head / Staff see only assigned unit in tree, org-unit list, and documents | Dept Head, Staff | [ ] |
| Tampered `orgUnitId` on document list returns 403 for out-of-scope unit | Dept Head | [ ] |

---

## 3. Documents

### Folders (`/documents`)

| Test case | Role | Done |
|-----------|------|------|
| Tree loads; folder selection filters table and breadcrumbs | All | [ ] |
| Create, rename, delete empty folder | All | [ ] |
| Rename folder updates document Location column and stored path for docs in subtree | Admin, Dept Head | [ ] |
| Edit Details header location matches selected folder dropdown | Admin, Dept Head | [ ] |
| Delete non-empty folder: blocked (Staff), allowed (Admin / Dept Head) | All | [ ] |
| Folders scoped to user's Org Unit | Staff, Dept Head | [ ] |

### Upload

| Test case | Role | Done |
|-----------|------|------|
| PDF or Google Drive link upload with folder, category, manual document code, requisitioners, description, and ≥1 keyword | All | [ ] |
| Document code required; letters, numbers, hyphens only; unique across system | All | [ ] |
| Google Drive–only upload (no PDF) counts toward Documents but not file storage quota | All | [ ] |
| Edit Details updates document code, metadata, requisitioners, and optional Drive link | Admin, Dept Head | [ ] |
| Non-PDF, missing fields, duplicate name, and out-of-scope folder rejected | All | [ ] |
| File over configured upload limit (default 15 MB) rejected | All | [ ] |
| Upload blocked when global or Office Unit storage quota exceeded | All | [ ] |

### Notifications & storage alerts

| Test case | Role | Done |
|-----------|------|------|
| Notification bell visible in header; badge count readable (white text on red) | All | [ ] |
| Storage warning/alert notifications appear at 80/90/95/100% physical usage thresholds | All | [ ] |
| Admin sees allocation alerts at 90/100% of top-level allocated quotas | Admin | [ ] |
| Admin sees additional 90% administration notice | Admin | [ ] |
| **Clear** removes notifications and resets badge count | All | [ ] |
| Threshold notifications do not duplicate on refresh | All | [ ] |
| Admin can configure upload limit and system storage quota (Settings → System) | Admin | [ ] |
| System storage quota preset dropdown (5/15/100/500 GB, 1/3/5 TB, Custom) saves correct MB value | Admin | [ ] |
| Non-preset system quota (e.g. 400 MB) loads as Custom with MB input | Admin | [ ] |
| Upload button disabled when global quota exceeded | All | [ ] |

### Table & filters

| Test case | Role | Done |
|-----------|------|------|
| Search, category filter, date range, and pagination work | All | [ ] |
| Preview, download, rename | All | [ ] |
| Edit Details (folder, metadata, keywords): Admin / Dept Head only | Admin, Dept Head | [ ] |
| Delete → Recycle Bin: Admin / Dept Head only | Admin, Dept Head | [ ] |

### Categories

| Test case | Role | Done |
|-----------|------|------|
| Create, rename, delete (blocked if in use); scoped to Org Unit | All | [ ] |
| Parent Dept Head can manage categories in child Office Units via Manage Categories | Dept Head | [ ] |

---

## 4. Document Assistant

| Test case | Role | Done |
|-----------|------|------|
| Opens on Documents page; greeting and help work | All | [ ] |
| Count / list / code search; max 5 results + total | All | [ ] |
| "This folder" / "this category" with page context | All | [ ] |
| Follow-up after code (e.g. `120-12` → `What is about?`) | All | [ ] |
| RBAC respected; no out-of-scope results | Staff, Dept Head | [ ] |
| Parent Dept Head assistant counts/search include child-unit documents | Dept Head | [ ] |
| Dept Head can ask Requisitioners Directory questions (scoped tagged counts) | Dept Head | [ ] |
| Staff Requisitioners Directory chatbot questions politely refused | Staff | [ ] |
| Child Dept Head / Staff assistant excludes parent and sibling units | Dept Head, Staff | [ ] |

> More queries: [CHATBOT_CAPABILITIES.md](../CHATBOT_CAPABILITIES.md)

---

## 5. Public Assistant

| Test case | Role | Done |
|-----------|------|------|
| Opens on login page; suggested questions work | Public | [ ] |
| FAQ answers (upload, roles, login); file queries ask to log in | Public | [ ] |
| Cooldown, duplicate block, session limit | Public | [ ] |

---

## 6. User Management (`/users`)

| Test case | Role | Done |
|-----------|------|------|
| List, search, pagination | Admin, Dept Head | [ ] |
| Create user + activation email; optional password activates immediately | Admin, Dept Head | [ ] |
| Resend activation | Admin, Dept Head | [ ] |
| Admin: all roles. Dept Head: Staff in accessible org subtree; child Heads read-only | Admin, Dept Head | [ ] |
| Parent Dept Head lists and manages Staff in child Office Units | Dept Head | [ ] |
| Parent Dept Head can assign new Staff to child Office Unit on create | Dept Head | [ ] |
| Child Dept Head sees only own-unit users; cannot access parent unit staff | Dept Head | [ ] |
| Tampered orgUnitId filter on user list returns 403 | Dept Head | [ ] |
| Deactivate / reactivate; cannot remove last active Admin | Admin | [ ] |
| Staff blocked from route → `/error/403` | Staff | [ ] |

---

## 7. Requisitioners Directory (`/employees`)

| Test case | Role | Done |
|-----------|------|------|
| Admin: list, search, Add/Edit/Delete, global Tagged Documents counts | Admin | [ ] |
| Admin: View Documents modal lists all tagged documents | Admin | [ ] |
| Dept Head: read-only list with scoped Tagged Documents counts | Dept Head | [ ] |
| Dept Head: View Documents shows only accessible org units; Edit/Delete hidden | Dept Head | [ ] |
| Dept Head: directory API mutations return 403 | Dept Head | [ ] |
| Staff: no sidebar link; direct URL → `/error/403` | Staff | [ ] |
| Staff: `GET /api/employees?search=` works during document upload | Staff | [ ] |
| Staff: browse directory without search returns 403 + audit | Staff | [ ] |
| Cross-org tags: dept head sees scoped count only | Dept Head | [ ] |
| Directory-selected requisitioner on document: name/number read-only; remove to change person | Admin, Dept Head | [ ] |
| Manual requisitioner: editable; duplicate employee number blocked with required message | Admin, Dept Head | [ ] |
| Manual requisitioner: similar existing name blocked on save | Admin, Dept Head | [ ] |
| Document metadata edit does not create orphan directory rows | Admin | [ ] |
| Admin: `find_duplicate_requisitioners` report identifies split rows for cleanup | Admin | [ ] |
| Edit modal shows Tagged Documents count | Admin | [ ] |
| Tagged requisitioner: employee number field locked with helper message | Admin | [ ] |
| Tagged requisitioner: name edit still works and cascades to document tags | Admin | [ ] |
| Untagged requisitioner: employee number editable | Admin | [ ] |
| Admin override: reason required, number editable, audit log `UPDATE_EMPLOYEE_NUMBER_OVERRIDE` | Admin | [ ] |

---

## 8. Org Units (`/org-units`) — Admin only

| Test case | Role | Done |
|-----------|------|------|
| CRUD org units and org types | Admin | [ ] |
| Table shows Envelope, To Children, Pool Available, Used (files), Documents, File Space Left | Admin | [ ] |
| Type filter (College / Department / Office) updates table and impact summary counts | Admin | [ ] |
| Parent row: e.g. CISC 15 GB envelope, 5 GB to children, 10 GB pool available | Admin | [ ] |
| Child row: quota shows "from {parent}"; To Children shows 0 MB; Pool Available shows full envelope | Admin | [ ] |
| Parent Used shows subtree total with "includes child units" when files are in child | Admin | [ ] |
| Child unit has parent set (not top-level) when hierarchical model intended | Admin | [ ] |
| Add Office Unit disabled when 0 MB top-level allocation headroom remains | Admin | [ ] |
| Modal shows parent/system allocation headroom; child note about parent envelope | Admin | [ ] |
| Create/update blocked with clear error when quota exceeds remaining allocation | Admin | [ ] |
| Audit log records allocation validation failure and quota updates | Admin | [ ] |
| Allocation threshold bell alerts at 90% and 100% of allocated quotas | Admin | [ ] |
| Dept Head / Staff blocked | Dept Head, Staff | [ ] |

---

## 9. Audit Logs (`/audit-logs`) — Admin only

| Test case | Role | Done |
|-----------|------|------|
| List, search, filters (action, role, org unit, date range) | Admin | [ ] |
| Export Excel; key actions logged (login, upload, delete, edit) | Admin | [ ] |
| Dept Head / Staff blocked | Dept Head, Staff | [ ] |

---

## 10. Recycle Bin (`/recycle-bin`)

| Test case | Role | Done |
|-----------|------|------|
| List; filter documents / folders | Admin, Dept Head | [ ] |
| Deleted document/folder shows correct folder path in Location column | Admin, Dept Head | [ ] |
| Restore item | Admin, Dept Head | [ ] |
| Permanent delete requires typing `DELETE <filename>` exactly; button disabled until match | Admin, Dept Head | [ ] |
| Wrong confirmation shows inline error; API returns 400; failed attempt in Audit Logs | Admin, Dept Head | [ ] |
| Raw `DELETE /api/recycle-bin/delete` without confirmation returns 400 | Admin | [ ] |
| Dept Head scoped to org; Staff blocked | All roles | [ ] |
| Row checkboxes and Select All (current page only) | Admin, Dept Head | [ ] |
| Bulk toolbar appears when items selected; hidden when none | Admin, Dept Head | [ ] |
| Bulk restore mixed docs/folders; toast shows total restored | Admin, Dept Head | [ ] |
| Bulk delete requires `DELETE N ITEM(S)`; shows storage summary | Admin, Dept Head | [ ] |
| Selecting parent folder + child doc dedupes without error | Admin, Dept Head | [ ] |
| Per-row Restore/Delete still works alongside bulk actions | Admin, Dept Head | [ ] |

---

## 11. Settings

| Test case | Role | Done |
|-----------|------|------|
| Change password; wrong current / mismatch errors | All | [ ] |
| Success logs out; login with new password works | All | [ ] |

---

## 12. Security & UI

| Test case | Role | Done |
|-----------|------|------|
| Sidebar and routes match role (Staff: no directory link) | All | [ ] |
| Unauthorized protected route redirects to `/error/403` | Staff, Dept Head | [ ] |
| No out-of-scope Org Unit access (Staff: own unit; Dept Head: subtree only) | Staff, Dept Head | [ ] |
| Unauthenticated API returns 401 | All | [ ] |
| Empty states and upload errors handled cleanly | All | [ ] |

---

## 13. Backup Management (`/backup`)

| Test case | Role | Done |
|-----------|------|------|
| Admin sees Backup Management under Administration sidebar | Admin | [ ] |
| Download Database Backup → `.sql` file saves locally | Admin | [ ] |
| Download Media Backup → `.zip` file saves locally | Admin | [ ] |
| Audit Logs show `BACKUP_DATABASE_DOWNLOADED` / `BACKUP_MEDIA_DOWNLOADED` | Admin | [ ] |
| Dept Head / Staff: route blocked → `/error/403` | Dept Head, Staff | [ ] |
| Unauthorized API call returns 403 | Dept Head, Staff | [ ] |

---

## Alpha ready when

- [ ] Auth, upload, document CRUD, RBAC, and recycle restore all pass
- [ ] Admin, Dept Head, and Staff smoke paths done
- [ ] No open critical / high bugs

---

*June 2026*
