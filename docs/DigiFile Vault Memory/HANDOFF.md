# DFS Handoff

Living task log for DigiFile development. For ongoing data rules (document codes, employee numbers, requisitioners), see [DATA_MIGRATION_POLICY.md](./DATA_MIGRATION_POLICY.md).

> **Related notes:** [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) · [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) · [ALPHA_TEST_CHECKLIST.md](./ALPHA_TEST_CHECKLIST.md) · [DOCKER_SETUP.md](./DOCKER_SETUP.md) · [CHATBOT_CAPABILITIES.md](./CHATBOT_CAPABILITIES.md)

---

## October 13, 2026 checkpoint

### Completed

- Removed confirmed dead backend helpers, unused frontend exports and components, the disconnected legacy stylesheet, and the empty legacy account test module.
- Removed unused PostgreSQL and React Grab dependencies. React Grab remains documented as an optional development install.
- Consolidated the duplicate `OrgUnitAllocationRow` TypeScript type and removed redundant PyMySQL initialization from Django settings.
- Updated media backups so ZIP folders use Office/Suboffice and DigiFile folder names instead of numeric/date storage paths.
- Added collision-safe archive names, invalid filename sanitization, and backup service tests.
- Moved the Docker and chatbot notes into this Obsidian vault and repaired their related-document links.
- Pinned local backend setup to Django 4.2 because this project currently supports the XAMPP/MySQL-compatible Django 4.2 stack.

### Verification

- Frontend production build passed.
- Backend backup tests passed against the local environment.
- TypeScript checking still has seven pre-existing errors in requisitioner and dialog component typings; these were not hidden or changed during cleanup.
- React Doctor 0.9.18 scanned 115 frontend files: score **45/100**, 145 warnings. The first planned repair batch is form labels, icon-button names, keyboard-accessible folder rows, and an Office Unit submit re-entry guard.

### React Doctor batch 1

- Connected user and category form labels to their controls.
- Added accessible names to icon-only assistant, category, requisitioner, password, folder, and recycle-bin controls.
- Made folder rows native keyboard-accessible buttons without nesting the row action menu inside another button.
- Guarded Office Unit create/edit submission against double-click re-entry.
- Full rescan before the final folder adjustment: **48/100**, 116 warnings, down from 145, with accessibility warnings reduced from 31 to 1.
- The follow-up changed-file scan cleared that last accessibility warning and reports only two pre-existing component-complexity advisories. The frontend production build passes.

### Plan after batch 1

Review and fix the confirmed effect lifecycle warnings in small batches, rerunning React Doctor and the relevant frontend checks after each batch. Treat the localStorage authentication warning as a separate backend/frontend authentication design change, not part of the effect cleanup.

### React Doctor batch 2

- Stabilized the auto-logout callbacks so its activity listeners always use current authentication and navigation state.
- Added cleanup guards to Upload Dialog folder and system-setting requests so closed dialogs cannot receive stale updates.
- Added explicit PDF object-URL cleanup when a requisitioner preview changes or unmounts.
- Full rescan: **48/100**, 97 warnings, down from 116 after batch 1 and 145 initially. The production build passes.
- React Doctor still flags the requisitioner `createObjectURL` call even though the adjacent cleanup effect revokes that URL; treat this instance as a verified false positive unless its lifecycle changes.

### Next task after batch 2

Fix request races and missing dependencies in the audit logs, dashboard, documents, Office Units, recycle bin, and users list effects as one shared list-page batch.

### React Doctor batch 3

- Added optional `AbortSignal` support to the existing API GET helper.
- Cancelled effect-owned requests when list pages unmount or their filters, pagination, or scope change.
- Stabilized fetch callbacks and dependency lists for Audit Logs, Dashboard, Documents, Office Units, Recycle Bin, and Users.
- Preserved manual refresh and post-mutation reload behavior without cancellation signals.
- Full rescan: **49/100**, 88 warnings, down from 97 after batch 2 and 145 initially. The production build passes and TypeScript reports only the same seven pre-existing errors.
- React Doctor reports seven loading-reset warnings even though every reported reset remains inside `finally`; the conditional prevents an aborted request from clearing the loading state of its replacement request.

### Next task after batch 3

Fix the remaining recycle-bin async effect and then take the small, low-risk performance findings: lazy state initialization, stable context values, and the shared `Intl.DateTimeFormat` instance.

### React Doctor batch 4

- Added cancellation to the bulk permanent-delete summary request.
- Made the requisitioner draft initializer lazy so it runs only during initial state creation.
- Memoized Category and Auth context values; stabilized Auth actions used by consumers such as auto-logout.
- Reused one document-table `Intl.DateTimeFormat` instance and corrected current-page breadcrumb semantics.
- Full rescan: **49/100**, 82 warnings, down from 88 after batch 3 and 145 initially. Accessibility warnings are now zero and the production build passes.
- The bulk-delete request is guarded and aborted correctly, but React Doctor still reports its state-after-await pattern and conditional `finally` loading reset.

### Next task after batch 4

Resolve the seven existing TypeScript errors before further structural Doctor cleanup. After the frontend type check is clean, evaluate the remaining state-reset warnings individually; do not split large components merely to increase the Doctor score.

### React Doctor batch 5

- Fixed suffix-option inference while retaining support for legacy requisitioner values.
- Reused the existing shared `Document` type for requisitioner document previews.
- Migrated the notification popover and three recycle-bin dialog descriptions from obsolete `asChild` props to Base UI's `render` API.
- `npx tsc --noEmit` now passes with zero errors; the production build also passes.
- Full React Doctor baseline remains **49/100** with 82 warnings because this batch repaired compiler compatibility rather than Doctor-counted findings.

### Next task after batch 5

Review the remaining prop-driven state resets in dialogs and drawers. Keep reset behavior that intentionally clears forms on close; change only cases that can overwrite active user input or create an effect chain.

### React Doctor security batch 6

- Removed access and refresh tokens from `localStorage`; access tokens now live only in module memory.
- Login sets the one-day refresh token in an HttpOnly, SameSite cookie and no longer returns it in JSON.
- Refresh accepts only that cookie, logout clears it, and the direct token-pair endpoint was removed so browser code cannot obtain a refresh token.
- Session rehydration now exchanges the cookie for a new in-memory access token before loading the current user.
- Restricted credentialed CORS to `FRONTEND_URL` by default; deployments can supply `CORS_ALLOWED_ORIGINS` as a comma-separated list.
- Added backend regression tests for cookie flags, refresh behavior, logout cleanup, and removal of the token-pair endpoint.
- Validation: four focused backend tests, `npx tsc --noEmit`, the production build, and Django's production-URL system check all pass.
- Fresh React Doctor result: **56/100**, 81 warnings (up from 49/100 and down from 82 warnings). The local-storage token warning is gone; the remaining two security warnings are the PDF iframe sandbox findings.
- Cookie and CORS defaults are derived from `FRONTEND_URL`, including the production `/digifile/api/` cookie path.

### Next task after security batch 6

Manually verify login, reload, automatic refresh, and logout against the configured MySQL/XAMPP backend.

### React Doctor security batch 7

- Sandboxed both local PDF preview iframes with only `allow-same-origin`, preserving blob rendering without permitting scripts, forms, popups, navigation, or frame-triggered downloads.
- This closes the final two React Doctor security findings in `DocumentsPage` and `RequisitionerDocumentsDialog`.
- Validation: `npx tsc --noEmit` and the production build pass. React Doctor reports **79 issues** (down from 81) and no Security category; its score API timed out, so the numeric score was unavailable for this scan.

### Reliability batch 8

- Added request cancellation to the requisitioner-documents dialog so an old employee or closed dialog cannot apply a late response.
- Added lifecycle cleanup for the Documents page's active PDF blob URL, including navigation/unmount.
- Added regression coverage for production `Secure` refresh cookies and `/digifile/api/` cookie-path derivation.
- Validation: five focused backend tests, `npx tsc --noEmit`, and the production build pass. React Doctor is now **60/100** with 79 warnings and no Security category.
- React Doctor no longer reports the Documents-page object URL. Its requisitioner and profile object-URL warnings remain false positives because both URLs are revoked by effect cleanup.

### LAN showcase configuration

- Development API URLs now replace a configured `localhost` hostname with the hostname used to open Vite, so both `192.168.0.171:5173` and `172.16.0.68:5173` call the matching host on port 8000.
- The local backend environment allows both LAN hosts and their Vite CORS origins, with `AUTH_REFRESH_COOKIE_SECURE=False` for HTTP-only development.
- Removed the PDF iframe sandbox because it prevented the browser's built-in PDF viewer from rendering. This intentionally restores the two React Doctor iframe security warnings for the LAN showcase.
- Production still defaults to Secure refresh cookies whenever `DEBUG=False`; do not copy the development cookie override into the server environment.
- The original fetch failure was the running Django process binding only to `127.0.0.1:8000`. It was replaced with a single `0.0.0.0:8000 --noreload` process; both LAN IPs now reach the API and both CORS preflights return the matching origin with credentials enabled.
- `python manage.py runserver` now defaults to `0.0.0.0:8000`; an explicitly supplied address remains unchanged. This prevents later manual restarts from silently returning the backend to localhost-only access.

### React Doctor reliability and duplication cleanup

- Fixed the confirmed bug behavior behind the prop-reset, effect-chain, changing-callback, stale bulk-summary, and unstable requisitioner-key findings.
- Stateful dialogs now mount only while open, so document, requisitioner, assistant, and permanent-delete state resets naturally without stale prop-driven effects.
- Extracted shared authentication introduction/header/success sections and a shared target-folder selector; React Doctor's four duplicate-JSX findings are now zero.
- Validation: `npx tsc --noEmit` and the production build pass. The latest full scan reports **60 findings**: 26 maintainability, 21 performance, 11 bug, and 2 intentional LAN PDF iframe security warnings. The score API timed out.
- Manual test focus: document editing, assistant reopen/reset, requisitioner search/pagination and PDF preview, employee-directory mutations, requisitioner row editing/removal, and single/bulk permanent deletion.

### Media backup ZIP cleanup

- Removed `MEDIA_BACKUP_MANIFEST.csv` from generated media backup ZIPs and updated the focused backup test.
- Media files remain grouped under readable `documents/<Office>/<Suboffice>/<Folder>/` paths, with unlinked documents under `_unlinked/documents/`.
- Restore remains manual: without the manifest, database file paths and readable ZIP paths must be reconciled manually when rebuilding `MEDIA_ROOT`.

---

## August 2026 schema and Docker handoff

### Summary

- Standardized custom DB table names to **plural snake_case** via `Meta.db_table`
- Squashed naming into each app's **`0001_initial`** (no `0002` rename migrations)
- Upgraded Docker MySQL image from **`8.0` → `8.4`** (required by Django 6.x)

No REST API or frontend changes — only MySQL table names and dev infrastructure.

---

## Database table naming

Custom tables (Django `auth_*` / `django_*` unchanged):

| Model | Table |
|-------|-------|
| `User` | `users` |
| User M2M | `user_groups`, `user_permissions` |
| `OrgType` / `OrgUnit` | `org_types`, `org_units` |
| `Category` / `Folder` / `Document` | `categories`, `folders`, `documents` |
| `DocumentRequisitioner` | `document_requisitioners` |
| `Employee` | `employees` |
| `AuditLog` | `audit_logs` |
| `Notification` / `StorageThresholdState` | `notifications`, `storage_threshold_states` |
| `SystemSettings` | `system_settings` |

Full reference: [DEVELOPER_GUIDE.md — Database table naming](./DEVELOPER_GUIDE.md#database-table-naming)

---

## Code and migrations

| Area | Change |
|------|--------|
| `backend/*/models.py` | `Meta.db_table` on all custom models; `User` M2M uses `user_groups` / `user_permissions` |
| `backend/*/migrations/0001_initial.py` | `db_table` in each `CreateModel` `options` |
| Removed | All `0002_*` table-rename migration files (squashed into `0001_initial`) |

When adding a new model, set `db_table` in `Meta` and include it in the app's initial migration.

---

## Docker and local dev

- **MySQL image:** `mysql:8.4` in `docker-compose.dev.yml`, `docker-compose.yml`, `docker-compose.prod.yml`
- **Fresh dev database** (after pull, or if DB still has old table names like `accounts_user`):

  ```powershell
  docker compose -f docker-compose.dev.yml down -v
  docker compose -f docker-compose.dev.yml up --build
  ```

- **Normal restart** (keep data): `docker compose -f docker-compose.dev.yml up`
- **Admin account:** auto-created on startup when `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD` are set in `backend/.env`

See [DOCKER_SETUP.md](./DOCKER_SETUP.md) for full setup and troubleshooting.

---

## Legacy SQL backups

Do **not** restore old dumps (e.g. `backend/tmp/backups/DFS_DATABASE_20260606_083528.sql`) — they use legacy table names (`accounts_user`, `orgunits_orgunit`, etc.).

New backups from `GET /api/backups/database` use the current schema.

---

## Docs updated in this change

- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) — database table naming section
- [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) — Appendix B (database tables)
- [DOCKER_SETUP.md](./DOCKER_SETUP.md) — MySQL 8.4 and migration notes
- [VESTA_DEPLOYMENT.md](./VESTA_DEPLOYMENT.md) — MySQL 8.4
- [README.md](../README.md), [backend/installation process.md](../backend/installation%20process.md)
