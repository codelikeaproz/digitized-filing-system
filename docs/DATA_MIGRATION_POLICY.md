# DFS V2 Data Migration Policy



This document defines how legacy data is handled after the June 2026 stakeholder changes.



## Document codes (manual entry)



- **Database:** `Document.code` is a unique, user-entered identifier on the initial schema (`documents.0001_initial`).

- **Policy:** Document codes are **not** auto-generated. Uploaders and editors enter codes manually. Category abbreviations and `DocumentSequence` are not part of the schema.

- **User impact:** Search, upload, edit, and AI assistant continue to reference document codes when provided.



## Document status (removed)



- **Database:** `Document.status` is not on the initial schema.

- **Policy:** No data migration required; all live values were `Received`.



## Employee numbers (format change)



New institutional format: `Letter-Year-Code` (e.g. `D-2122-GCM`, `D-2123-GCMD`).



| Context | Legacy numeric values | New entries |

|---------|----------------------|-------------|

| User accounts | Grandfathered on edit when unchanged | Must use institutional format |

| Document requisitioners (optional) | Allowed when provided | Institutional format or legacy numeric |

| Requisitioners Directory | N/A (new table) | Institutional format required; **Dept Head:** read-only browse with org-unit–scoped tagged counts |



**Migration approach:** No bulk update script is run automatically. Administrators should update user and Requisitioners Directory records to the new format during normal maintenance. Legacy numeric requisitioner values on existing documents remain valid.



## Document requisitioner tags (FK model)



- **Database:** `DocumentRequisitioner.employee` FK and `source` (`directory` | `manual`) are on the initial schema (`documents.0001_initial`). Denormalized name/number fields remain as display snapshots.

- **Backfill:** When upgrading a legacy database (pre-FK schema), link existing tags to `Employee` rows manually or via a one-off script when employee number or normalized name matches unambiguously. Fresh installs do not run a backfill migration.

- **Directory-selected tags:** Store `employeeId`; name and employee number are read-only on the document; snapshots refresh from the master record on save.

- **Manual tags:** Editable on the document; on save the server creates a directory row **only if no duplicate** employee number or similar name exists. Document edits **never** update master `Employee` records.

- **Duplicate cleanup:** Run `python manage.py find_duplicate_requisitioners` to report split rows (e.g. same person with a number row and a name-only row). Consolidate references manually by linking tags to the canonical `employee_id`, then deactivate orphan directory rows.

- **Directory employee number lock:** Once a requisitioner is tagged on ≥1 document, employee number is locked on directory edit. Name changes remain allowed and cascade to linked tags. Admins may override the lock with a documented reason; overrides are audit-logged.



## Google Drive links (added)



- **Database:** `Document.google_drive_link` and optional `Document.file` are on the initial schema.

- **Policy:** Existing documents keep their PDF files. New link-only documents store no file and do not count toward storage quota usage.



## Database table names

See [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md#database-table-naming) for the current schema. August 2026 implementation notes: [HANDOFF.md](./HANDOFF.md).

