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
| Dept Head | + Users (Staff in org), Recycle Bin |
| Admin | + Org Units, Audit Logs, full Recycle Bin |

**Sign-off:** Tester __________ · Date __________ · Pass / Fail __________

---

## 1. Authentication

| Test case | Role | Done |
|-----------|------|------|
| Login, logout, session refresh, protected route redirect | All | [ ] |
| Forgot / reset password flow works | All | [ ] |
| New user activation via `/set-password/...` | Admin-created | [ ] |
| Auto-logout after 10 min idle | All | [ ] |

---

## 2. Dashboard

| Test case | Role | Done |
|-----------|------|------|
| Stats load; counts update after upload | All | [ ] |
| Admin-only cards (Org Units, Users) visible to Admin only | Admin | [ ] |

---

## 3. Documents

### Folders (`/documents`)

| Test case | Role | Done |
|-----------|------|------|
| Tree loads; folder selection filters table and breadcrumbs | All | [ ] |
| Create, rename, delete empty folder | All | [ ] |
| Delete non-empty folder: blocked (Staff), allowed (Admin / Dept Head) | All | [ ] |
| Folders scoped to user's Org Unit | Staff, Dept Head | [ ] |

### Upload

| Test case | Role | Done |
|-----------|------|------|
| PDF upload with folder, category, code, and ≥1 keyword | All | [ ] |
| Non-PDF, missing fields, duplicate name, and out-of-scope folder rejected | All | [ ] |

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

---

## 4. Document Assistant

| Test case | Role | Done |
|-----------|------|------|
| Opens on Documents page; greeting and help work | All | [ ] |
| Count / list / code search; max 5 results + total | All | [ ] |
| "This folder" / "this category" with page context | All | [ ] |
| Follow-up after code (e.g. `120-12` → `What is about?`) | All | [ ] |
| RBAC respected; no out-of-scope results | Staff, Dept Head | [ ] |

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
| Create user + activation email; resend activation | Admin, Dept Head | [ ] |
| Admin: all roles. Dept Head: Staff in own org only | Admin, Dept Head | [ ] |
| Deactivate / reactivate; cannot remove last active Admin | Admin | [ ] |
| Staff blocked from route | Staff | [ ] |

---

## 7. Org Units (`/org-units`) — Admin only

| Test case | Role | Done |
|-----------|------|------|
| CRUD org units and org types | Admin | [ ] |
| Dept Head / Staff blocked | Dept Head, Staff | [ ] |

---

## 8. Audit Logs (`/audit-logs`) — Admin only

| Test case | Role | Done |
|-----------|------|------|
| List, search, filters (action, role, org unit, date range) | Admin | [ ] |
| Export Excel; key actions logged (login, upload, delete, edit) | Admin | [ ] |
| Dept Head / Staff blocked | Dept Head, Staff | [ ] |

---

## 9. Recycle Bin (`/recycle-bin`)

| Test case | Role | Done |
|-----------|------|------|
| List; filter documents / folders | Admin, Dept Head | [ ] |
| Restore and permanent delete | Admin, Dept Head | [ ] |
| Dept Head scoped to org; Staff blocked | All roles | [ ] |

---

## 10. Settings

| Test case | Role | Done |
|-----------|------|------|
| Change password; wrong current / mismatch errors | All | [ ] |
| Success logs out; login with new password works | All | [ ] |

---

## 11. Security & UI

| Test case | Role | Done |
|-----------|------|------|
| Sidebar and routes match role | All | [ ] |
| No cross–Org Unit document access | Staff, Dept Head | [ ] |
| Unauthenticated API returns 401 | All | [ ] |
| Empty states and upload errors handled cleanly | All | [ ] |

---

## Alpha ready when

- [ ] Auth, upload, document CRUD, RBAC, and recycle restore all pass
- [ ] Admin, Dept Head, and Staff smoke paths done
- [ ] No open critical / high bugs

---

*May 2026*
