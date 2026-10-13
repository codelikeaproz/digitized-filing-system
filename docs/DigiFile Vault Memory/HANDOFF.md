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
- Added `MEDIA_BACKUP_MANIFEST.csv`, collision-safe archive names, invalid filename sanitization, and backup service tests.
- Moved the Docker and chatbot notes into this Obsidian vault and repaired their related-document links.
- Pinned local backend setup to Django 4.2 because this project currently supports the XAMPP/MySQL-compatible Django 4.2 stack.

### Verification

- Frontend production build passed.
- Backend backup tests passed against the local environment.
- TypeScript checking still has seven pre-existing errors in requisitioner and dialog component typings; these were not hidden or changed during cleanup.
- React Doctor 0.9.18 scanned 115 frontend files: score **45/100**, 145 warnings. The first planned repair batch is form labels, icon-button names, keyboard-accessible folder rows, and an Office Unit submit re-entry guard.

### Next task

Fix the confirmed React Doctor findings in small batches, rerunning React Doctor and the relevant frontend checks after each batch. Treat the localStorage authentication warning as a separate backend/frontend authentication design change, not part of the accessibility cleanup.

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
