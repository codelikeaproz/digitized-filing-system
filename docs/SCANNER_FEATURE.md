# Scanner Feature Guide

This guide explains how the DFS scanner workflow works, and how to enable/disable it safely in both backend and frontend.

---

## 1. Current design

Scanner support in DFS has two layers:

1. **Backend scanner APIs** (Django, Scanner Bridge integration)
2. **Frontend scanner UI** (Upload dialog scanner flow)

You can enable them independently, but for a complete workflow both should be enabled.

---

## 2. Feature flags

### Backend flag

Set in `.env`:

```env
ENABLE_SCANNER_FEATURE=true
```

- `true`  -> scanner routes are mounted (`/api/scanner/*`, `/api/scan-jobs*`)
- `false` -> scanner routes are not exposed

Implementation:
- `backend/config/settings.py` -> `ENABLE_SCANNER_FEATURE`
- `backend/documents/urls.py` -> scanner URL registration guarded by this flag

### Frontend flag

Set in `.env`:

```env
VITE_ENABLE_SCANNER=true
VITE_SCANNER_STATION_ID=SCANNER-PC-01
```

- `true`  -> scanner option appears in `UploadDialog`
- `false` -> scanner option shows disabled/testing state and manual upload is used

Implementation:
- `frontend/src/components/UploadDialog.tsx`

---

## 3. Required scanner bridge config

Set backend bridge token:

```env
SCANNER_BRIDGE_TOKEN=<strong-random-secret>
```

Scanner Bridge must send:

```http
X-Scanner-Token: <SCANNER_BRIDGE_TOKEN>
X-Scanner-Station: <station_id>
```

If token mismatch occurs, bridge requests are rejected with permission errors.

---

## 4. Scanner workflow (end-to-end)

1. User starts scanner flow in Upload dialog
2. Frontend creates a scan job via `POST /api/scan-jobs`
3. Scanner Bridge polls `GET /api/scan-jobs/pending`
4. Scanner Bridge uploads PDF via `POST /api/scan-jobs/{id}/upload`
5. Backend validates PDF and creates `Document` with `source="Scanned"`
6. Frontend polls `GET /api/scan-jobs/{id}` and marks success/failure

### Related endpoints

- `GET /api/scanner/stations`
- `POST /api/scanner/stations/heartbeat`
- `GET/POST /api/scan-jobs`
- `GET /api/scan-jobs/pending`
- `GET/PATCH /api/scan-jobs/{id}`
- `POST /api/scan-jobs/{id}/upload`
- `PATCH /api/scan-jobs/{id}/fail`

---

## 5. How to enable scanner for a new developer

1. Set environment variables:
   - `ENABLE_SCANNER_FEATURE=true`
   - `SCANNER_BRIDGE_TOKEN=<secret>`
   - `VITE_ENABLE_SCANNER=true`
   - `VITE_SCANNER_STATION_ID=<station-id>`
2. Start backend and frontend
3. Start Scanner Bridge service with matching token/station ID
4. Verify station heartbeat:
   - call `GET /api/scanner/stations`
   - station should report online
5. Test scan flow from Upload dialog

---

## 6. How to disable scanner safely

If your deployment does not use scanners:

- Backend: `ENABLE_SCANNER_FEATURE=false`
- Frontend: `VITE_ENABLE_SCANNER=false`

This prevents scanner endpoints from being exposed and keeps manual upload fully functional.

---

## 7. Troubleshooting

### Scanner button disabled in UI
- Check `VITE_ENABLE_SCANNER=true`
- Restart frontend dev server after changing env vars

### 403 from scanner endpoints
- Check `SCANNER_BRIDGE_TOKEN` and `X-Scanner-Token` match exactly

### No pending jobs found
- Confirm station IDs match (`VITE_SCANNER_STATION_ID` and bridge station header)

### Jobs stuck in WAITING_FOR_SCAN
- Confirm Scanner Bridge is running and watching incoming folder
- Check scanner station heartbeat endpoint and bridge logs

---

## 8. Notes for maintainers

- Keep scanner routes behind `ENABLE_SCANNER_FEATURE` for production safety.
- Do not hardcode scanner tokens in code or docs.
- Update this guide and `docs/API_DOCUMENTATION.md` when scanner behavior changes.
