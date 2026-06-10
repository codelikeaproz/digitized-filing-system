# Vesta Deployment Guide

Production deployment guide for **Digitized Filing System (DFS)** on a server using **Vesta CP**, **nginx**, and **Docker**.

> **Related:** [DOCKER_SETUP.md](../DOCKER_SETUP.md) (local dev) · [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) · [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

**Start here for CMU production:** [Quick deploy (recurring)](#quick-deploy-recurring)

### Quick deploy (recurring)

After one-time server setup (nginx, Docker, SSL — Sections 6–7), each deploy is:

**Frontend**

```bash
cd frontend
npm run build
```

Upload **contents** of `frontend/dist/` to:

```text
/home/admin/web/apps.cmu.edu.ph/public_html/digifile/
```

No manual `frontend/.env` edits needed — production URL is in `frontend/.env.production` (loaded automatically by `npm run build`).

**Backend** (first deploy or when secrets/env change)

```bash
cp backend/.env.production.example backend/.env
# Edit backend/.env — fill in secrets only (DJANGO_SECRET_KEY, DB_PASSWORD, EMAIL_*)
docker compose up -d --build
```

---

### CMU production (copy-paste reference)

Live site: [https://apps.cmu.edu.ph/digifile/](https://apps.cmu.edu.ph/digifile/) (DigiFile)

```env
# frontend/.env.production (already in repo — used by npm run build)
VITE_API_URL=https://apps.cmu.edu.ph/digifile

# backend/.env on server (copy from backend/.env.production.example)
ALLOWED_HOSTS=apps.cmu.edu.ph
FRONTEND_URL=https://apps.cmu.edu.ph/digifile
DEBUG=False
```

Upload built frontend to:

```text
/home/admin/web/apps.cmu.edu.ph/public_html/digifile/
```

---

## 1. Overview

### Recommended production layout

Vesta already provides **nginx on the host**. In production you typically use:

| Component | How it runs |
|-----------|-------------|
| **Vesta nginx** | Public HTTPS entry, serves React static files, reverse-proxies API and media |
| **Frontend** | Pre-built `frontend/dist/` copied to the Vesta web root (no Vite dev container) |
| **Backend container** | Django REST API (Gunicorn), connects to MySQL over Docker network |
| **MySQL container** | Database with a persistent Docker volume |

You do **not** need the local dev frontend container (`npm run dev` on port 5173) in production.

CMU hosts DigiFile under a **subpath** on the shared apps domain (`/digifile/`), not at domain root.

```text
Browser
   │
   ▼
Vesta nginx (apps.cmu.edu.ph)
   ──► /digifile/              → public_html/digifile/ (static SPA)
   ──► /digifile/api/, /media/ → backend container :8000
   ──► /digifile/admin/        → backend container (optional)

backend container ──► mysql container (DB_HOST=db)
```

### Local dev vs production

| | Local (`docker compose`) | Production (Vesta / CMU) |
|--|---------------------------|---------------------|
| Frontend | Vite dev server in Docker (:5173) | Static `dist/` on nginx |
| Backend | `runserver` (development only) | **Gunicorn** (recommended) |
| Database | MySQL container | MySQL container (or managed DB) |
| Public URL | `localhost` | `https://apps.cmu.edu.ph/digifile/` |
| Env files | `backend/.env`, `frontend/.env` | Same split; **production values** |

---

## 2. What to change — your URL (not localhost)

Use this section as a checklist when moving from local dev to Vesta. CMU production uses **`https://apps.cmu.edu.ph/digifile/`** on the shared `apps.cmu.edu.ph` host.

### 2.1 Quick rule

| Who sees it | Use |
|-------------|-----|
| **Users in the browser** | `https://apps.cmu.edu.ph/digifile/` (no `localhost`, no `:5173`, no public `:8000`) |
| **Email links** (reset password, activation) | Same public frontend URL |
| **Server internal only** (nginx → Docker) | `127.0.0.1:8000` is OK — users never type this |

```text
User browser     →  https://apps.cmu.edu.ph/digifile/
Email links      →  https://apps.cmu.edu.ph/digifile/set-password/...
API from browser →  https://apps.cmu.edu.ph/digifile/api/...
nginx (internal) →  http://127.0.0.1:8000  (backend container)
MySQL (internal) →  DB_HOST=db  (Docker service name)
```

---

### 2.2 Files you **must** change for production

#### A) Frontend build — on your **build machine**

Production settings are **already in the repo**. You do not need to create `frontend/.env` before deploy.

| File | Purpose |
|------|---------|
| `frontend/.env.development` | Used by `npm run dev` → `http://localhost:8000` |
| `frontend/.env.production` | Used by `npm run build` → `https://apps.cmu.edu.ph/digifile` |

**CMU subpath setup:** API is at `https://apps.cmu.edu.ph/digifile/api/...` on the same host as the SPA.

```bash
cd frontend
npm run build
```

Upload **`frontend/dist/`** contents to `public_html/digifile/`. Rebuild after any frontend code change — an old `dist/` built with dev settings will still call localhost.

> **Do not** put `.env` files on the Vesta web root. Only upload `dist/` contents.

---

#### B) `backend/.env` — on the **Vesta server** (loaded by Docker backend container)

Copy from `backend/.env.production.example` (CMU values pre-filled). **Never commit** `backend/.env` to Git.

| Variable | Dev example | Change to (CMU production) |
|----------|-------------|---------------------------|
| `DEBUG` | `True` | **`False`** |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,backend` | **`apps.cmu.edu.ph`** |
| `FRONTEND_URL` | `http://localhost:5173` | **`https://apps.cmu.edu.ph/digifile`** |
| `DJANGO_SECRET_KEY` | dev placeholder | **long random secret** |
| `DB_PASSWORD` | dev password | **strong production password** |
| `DB_HOST` | `db` | **`db`** (keep — Docker MySQL service name) |
| `DB_ENGINE` | `mysql` | **`mysql`** (keep) |
| `EMAIL_*` | test / empty | **real SMTP** for activation & reset emails |

Example production `backend/.env`:

```env
DJANGO_SECRET_KEY=replace-with-long-random-secret
DEBUG=False
ALLOWED_HOSTS=apps.cmu.edu.ph

DB_ENGINE=mysql
DB_NAME=dfs_project
DB_USER=dfs_user
DB_PASSWORD=your-strong-db-password
DB_HOST=db
DB_PORT=3306

FRONTEND_URL=https://apps.cmu.edu.ph/digifile

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=your_email@gmail.com
```

**`ALLOWED_HOSTS` note:** List the hostname users type in the browser (no `https://`, no path). For CMU, that is `apps.cmu.edu.ph` only.

Optional: keep `127.0.0.1` only if you run health checks on the server with `curl http://127.0.0.1:8000/...`. It is **not** your public URL.

---

#### C) Vesta CP — nginx / domain (server panel, not a repo file)

| Where in Vesta | What to set |
|----------------|-------------|
| **Web → Domain** | `apps.cmu.edu.ph` |
| **SSL** | Enable Let's Encrypt / certificate |
| **Document root** | Upload `dist/` into `public_html/digifile/` |
| **Nginx custom config** | Proxy `/digifile/api/` and `/digifile/media/` to backend (Section 7) |

Static files path on the server:

```nginx
alias /home/admin/web/apps.cmu.edu.ph/public_html/digifile/;
```

---

### 2.3 Subpath settings (already in the repo)

CMU hosts DigiFile at `/digifile/`, not domain root. These are **already configured** — no manual edits before each deploy:

| File | What it does |
|------|----------------|
| `frontend/vite.config.js` | `base: '/digifile/'` in production mode |
| `frontend/src/App.tsx` | `basename` derived from Vite `BASE_URL` |
| `frontend/src/lib/app-path.ts` | Subpath-safe redirects and public assets |

- `npm run dev` → `http://localhost:5173` (no subpath)
- `npm run build` → `https://apps.cmu.edu.ph/digifile/` (subpath baked in)

Without `base` and `basename`, the app may show a blank page, broken CSS/JS, or 404 on refresh. If you change the deploy subpath, update `vite.config.js` and `frontend/.env.production` together.

---

### 2.4 Files you usually **do not** change for URL

These are correct for Vesta/Docker even in production:

| File / setting | Value | Why |
|----------------|-------|-----|
| `docker-compose.yml` → `127.0.0.1:8000:8000` | Keep | Binds backend to server localhost; nginx proxies here |
| nginx `proxy_pass http://127.0.0.1:8000` | Keep | Internal hop from Vesta nginx to container |
| `backend/.env` → `DB_HOST=db` | Keep | Docker network name for MySQL container |
| `backend/config/settings.py` | No edit | Reads from `backend/.env` via env vars |
| `frontend/src/lib/api.ts` | No edit | Uses `VITE_API_URL` from build |
| `frontend/.env.example` | No edit on server | Template only; copy to `.env` and change values |

---

### 2.5 Source code fallbacks (no edit needed if `.env` is correct)

Some pages default to `127.0.0.1:8000` **only when `VITE_API_URL` is missing**:

- `frontend/src/lib/api.ts`
- `frontend/src/lib/backup.ts`
- `frontend/src/pages/auditlogs/AuditLogsPage.tsx`
- `frontend/src/pages/documents/DocumentsPage.tsx`

If you run `npm run build`, production `dist/` uses `frontend/.env.production` and will **not** use localhost.

---

### 2.6 Side-by-side example (CMU production)

Public site: **`https://apps.cmu.edu.ph/digifile/`**

| Setting | Wrong (dev left in prod) | Correct (CMU production) |
|---------|--------------------------|--------------------------|
| User opens app | `http://localhost:5173` | `https://apps.cmu.edu.ph/digifile/` |
| `frontend/.env` → `VITE_API_URL` | `http://localhost:8000` | `https://apps.cmu.edu.ph/digifile` |
| `backend/.env` → `FRONTEND_URL` | `http://localhost:5173` | `https://apps.cmu.edu.ph/digifile` |
| `backend/.env` → `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `apps.cmu.edu.ph` |
| Password email link | `http://localhost:5173/reset-password/...` | `https://apps.cmu.edu.ph/digifile/reset-password/...` |
| API from browser | `http://localhost:8000/api/...` | `https://apps.cmu.edu.ph/digifile/api/...` |
| nginx → backend (internal) | — | `http://127.0.0.1:8000` ✓ |

---

### 2.7 Alternative layout (API subdomain — not used at CMU)

If you ever host the API on a separate subdomain instead of a subpath:

| Setting | Value |
|---------|--------|
| SPA URL | `https://apps.cmu.edu.ph/digifile` |
| API URL | `https://api.apps.cmu.edu.ph` |
| `VITE_API_URL` | `https://api.apps.cmu.edu.ph` |
| `FRONTEND_URL` | `https://apps.cmu.edu.ph/digifile` |
| `ALLOWED_HOSTS` | `api.apps.cmu.edu.ph,apps.cmu.edu.ph` |

CMU uses the **same-host subpath** layout (Section 2.6), not a separate API subdomain.

---

### 2.8 Common mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Built `dist/` in dev mode or with stale output | API calls go to `localhost:8000` | Run `npm run build` (uses `.env.production` automatically) |
| `FRONTEND_URL` still `localhost:5173` | Email links open localhost | Set `FRONTEND_URL` in `backend/.env` |
| Domain missing from `ALLOWED_HOSTS` | **400 Disallowed Host** | Add `apps.cmu.edu.ph` to `ALLOWED_HOSTS` |
| `VITE_API_URL=http://backend:8000` | API fails in browser | Use public HTTPS URL |
| Missing `base` or `basename` | Blank page, broken assets, 404 on refresh | Set `base: '/digifile/'` and `basename="/digifile"` (Section 2.3) |
| Users open `:8000` directly | Bypasses nginx / SSL | Use domain only; keep 8000 internal |
| Uploaded old `dist/` after env change | Still broken until rebuild | Always rebuild after `VITE_API_URL` change |

---

### 2.9 Deployment order (recommended)

**One-time setup**

1. Create Vesta domain `apps.cmu.edu.ph` + SSL  
2. Configure **nginx** proxy for `/digifile/api/` and `/digifile/media/` (Section 7)  
3. `cp backend/.env.production.example backend/.env` → fill secrets  
4. Start Docker (`db` + `backend`)  

**Each frontend deploy**

5. Run **`npm run build`** in `frontend/`  
6. Upload **`dist/`** contents to `public_html/digifile/`  
7. Smoke test: login, upload, password reset email link  

---

## 3. Prerequisites

On the Vesta server:

- Docker and Docker Compose installed
- Vesta CP domain `apps.cmu.edu.ph` configured (SSL certificate recommended)
- Git access to the DFS repository (or deploy artifacts)
- Node.js on a build machine (your PC or CI) to run `npm run build`, **or** build `dist/` locally and upload it

---

## 4. Environment files

DFS uses **separate env files** for backend and frontend. Do not commit real secrets.

### 4.1 Frontend (build time)

Files in repo (no manual edit for normal deploy):

| File | Used by | `VITE_API_URL` |
|------|---------|----------------|
| `frontend/.env.development` | `npm run dev` | `http://localhost:8000` |
| `frontend/.env.production` | `npm run build` | `https://apps.cmu.edu.ph/digifile` |

**Important:**

- Production URL is baked in at build time from `.env.production`.
- CMU nginx proxies `/digifile/api/` on the **same domain** as the SPA.
- Do **not** use Docker-internal names like `http://backend:8000` — browsers cannot resolve them.
- Subpath settings (`base`, `basename`) are in the repo — see Section 2.3.

### 4.2 Backend (runtime, inside container)

Copy `backend/.env.production.example` to `backend/.env` on the server, then fill secrets.

File: `backend/.env`

```env
DJANGO_SECRET_KEY=<long-random-secret>
DEBUG=False
ALLOWED_HOSTS=apps.cmu.edu.ph,127.0.0.1

DB_ENGINE=mysql
DB_NAME=dfs_project
DB_USER=dfs_user
DB_PASSWORD=<strong-password>
DB_HOST=db
DB_PORT=3306

FRONTEND_URL=https://apps.cmu.edu.ph/digifile

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<smtp-user>
EMAIL_HOST_PASSWORD=<smtp-password>
DEFAULT_FROM_EMAIL=noreply@cmu.edu.ph

OPENROUTER_API_KEY=<optional-for-ai>
```

| Variable | Purpose |
|----------|---------|
| `ALLOWED_HOSTS` | Hostnames nginx sends in the `Host` header. Missing values cause **400 DisallowedHost**. |
| `FRONTEND_URL` | Base URL for password reset and activation email links. |
| `DB_HOST=db` | Docker Compose service name for MySQL (not `localhost` from inside the backend container). |
| `DEBUG` | Must be **`False`** in production. |

Optional backup temp directory:

```env
BACKUP_TEMP_DIR=/app/tmp/backups
```

---

## 5. Build and deploy the frontend

### 5.1 Build

On your machine or CI:

```bash
cd frontend
npm ci
npm run build
```

Production URL and subpath settings come from `frontend/.env.production` and `vite.config.js` (Section 2.3) — no manual `.env` setup required.

Output: `frontend/dist/` (HTML, JS, CSS, assets).

### 5.2 Upload to Vesta

Copy the **contents** of `dist/` (not the `dist` folder itself) into the CMU upload folder:

```text
/home/admin/web/apps.cmu.edu.ph/public_html/digifile/
```

After upload, `index.html` and `assets/` must sit **directly** under `digifile/`:

```text
public_html/digifile/
├── index.html
├── assets/
│   ├── index-xxxxx.js
│   └── index-xxxxx.css
└── img/
```

**How to upload:**

1. **Vesta File Manager:** `Web` → `apps.cmu.edu.ph` → `File Manager` → open `public_html/digifile/` → upload all files from `frontend/dist/`.
2. **SFTP / SCP:** Connect to the Vesta server and copy `dist/*` to `/home/admin/web/apps.cmu.edu.ph/public_html/digifile/`.
3. **Replace on update:** Delete old `assets/` (or entire folder contents) before uploading a new build to avoid stale JS/CSS files.

Vesta nginx serves this directory under `/digifile/`. The React app uses client-side routing, so nginx must fall back to `/digifile/index.html` for unknown paths (see Section 7).

**Do not** deploy the full `frontend/` source or run `npm run dev` on the server for production.

---

## 6. Backend and MySQL (Docker)

### 6.1 Production Compose (example)

Use a production-oriented Compose file on the server (separate from dev if needed). Example shape:

```yaml
services:
  db:
    image: mysql:8.0
    restart: always
    environment:
      MYSQL_DATABASE: dfs_project
      MYSQL_USER: dfs_user
      MYSQL_PASSWORD: ${DB_PASSWORD}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql

  backend:
    build: ./backend
    restart: always
    env_file:
      - ./backend/.env
    ports:
      - "127.0.0.1:8000:8000"   # bind to localhost; nginx proxies here
    volumes:
      - backend_media:/app/media
    depends_on:
      - db
    command: >
      sh -c "
      until nc -z db 3306; do sleep 2; done &&
      python manage.py migrate &&
      gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
      "

volumes:
  mysql_data:
  backend_media:
```

Notes:

- Expose backend on **`127.0.0.1:8000`** so only nginx on the host can reach it (not the public internet directly).
- Replace `runserver` with **Gunicorn** in production. Add `gunicorn` to `backend/requirements.txt` if not already installed.
- `backend_media` volume persists uploaded PDFs and profile images.

### 6.2 First deploy commands

```bash
docker compose up -d --build
docker compose exec backend python manage.py createsuperuser
```

Verify:

```bash
curl -I http://127.0.0.1:8000/api/docs/
```

---

## 7. Vesta nginx configuration

Add custom nginx rules for `apps.cmu.edu.ph` in Vesta (**Web → apps.cmu.edu.ph → Edit → Advanced** or custom template). Adjust paths if your Vesta admin username differs from `admin`.

### 7.1 CMU subpath layout (recommended)

SPA and API under `https://apps.cmu.edu.ph/digifile/`:

```nginx
# React SPA under /digifile/
location /digifile/ {
    alias /home/admin/web/apps.cmu.edu.ph/public_html/digifile/;
    try_files $uri $uri/ /digifile/index.html;
}

# Django API
location /digifile/api/ {
    proxy_pass http://127.0.0.1:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Uploaded files (PDFs, profile pictures)
location /digifile/media/ {
    proxy_pass http://127.0.0.1:8000/media/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Optional: Django admin
location /digifile/admin/ {
    proxy_pass http://127.0.0.1:8000/admin/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

With this layout:

```env
# frontend/.env at build time
VITE_API_URL=https://apps.cmu.edu.ph/digifile

# backend/.env
ALLOWED_HOSTS=apps.cmu.edu.ph,127.0.0.1
FRONTEND_URL=https://apps.cmu.edu.ph/digifile
```

### 7.2 Domain-root layout (alternative — not CMU)

Only use this if DigiFile is hosted at domain root (e.g. `https://digifile.cmu.edu.ph/`) instead of a subpath:

```nginx
location / {
    root /home/admin/web/apps.cmu.edu.ph/public_html;
    try_files $uri $uri/ /index.html;
}

location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /media/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 7.3 API subdomain layout (alternative — not CMU)

| URL | Purpose |
|-----|---------|
| `https://apps.cmu.edu.ph/digifile` | Static SPA |
| `https://api.apps.cmu.edu.ph` | Backend API |

- Build frontend with `VITE_API_URL=https://api.apps.cmu.edu.ph`
- Set `ALLOWED_HOSTS=api.apps.cmu.edu.ph,apps.cmu.edu.ph`
- Configure a separate Vesta domain or proxy block for the API subdomain pointing to `127.0.0.1:8000`

---

## 8. Backup management (Docker)

Admin backups run **inside the backend container**, not on your local PC or on the Vesta host directly.

| Backup type | What happens |
|-------------|----------------|
| **Database** | Backend runs `mysqldump` against `DB_HOST=db` → downloads `DFS_DATABASE_YYYYMMDD_HHMMSS.sql` to the admin browser |
| **Media** | Backend zips `/app/media` (Docker volume) → downloads `DFS_MEDIA_YYYYMMDD_HHMMSS.zip` to the admin browser |

Requirements:

- Backend image includes `default-mysql-client` (already in project `Dockerfile`).
- Admin role only; routes: `GET /api/backups/database`, `GET /api/backups/media`.
- Temp files are removed after download; nothing is stored long-term on the server.

Flow:

```text
Admin browser → Vesta nginx → backend container → MySQL / media volume → file download to admin PC
```

---

## 9. Deployment checklist

### Before go-live

- [ ] `DEBUG=False` in `backend/.env`
- [ ] Strong `DJANGO_SECRET_KEY` and database passwords
- [ ] `ALLOWED_HOSTS` includes `apps.cmu.edu.ph`
- [ ] `FRONTEND_URL=https://apps.cmu.edu.ph/digifile` (email links)
- [ ] `VITE_API_URL=https://apps.cmu.edu.ph/digifile`; frontend rebuilt and `dist/` uploaded
- [ ] `base: '/digifile/'` in `vite.config.js` and `basename="/digifile"` in `App.tsx`
- [ ] Backend uses Gunicorn, not `runserver`
- [ ] Backend bound to `127.0.0.1:8000` (or internal network only)
- [ ] SSL enabled in Vesta for `apps.cmu.edu.ph`
- [ ] Migrations applied; admin user created
- [ ] SMTP configured for activation / password reset emails
- [ ] `backend_media` and `mysql_data` volumes backed up (or use Backup Management UI)

### Smoke test

- [ ] Login at `https://apps.cmu.edu.ph/digifile/`
- [ ] Upload a PDF
- [ ] Download a document
- [ ] Admin: Backup Management downloads (database + media)
- [ ] Password reset email link opens `https://apps.cmu.edu.ph/digifile/...`

---

## 10. Updates and rollbacks

### Frontend update

```bash
# On build machine
cd frontend && npm run build
# Upload new dist/ contents to public_html/digifile/ (replace old files)
```

### Backend update

```bash
git pull
docker compose build backend
docker compose up -d backend
docker compose exec backend python manage.py migrate
```

Uploaded files remain in the `backend_media` volume across redeploys.

---

## 11. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| **400 DisallowedHost** | Domain missing from `ALLOWED_HOSTS` | Add `apps.cmu.edu.ph` to `backend/.env` |
| API calls fail / CORS | Wrong `VITE_API_URL` | Rebuild frontend with `https://apps.cmu.edu.ph/digifile` |
| API calls go to `backend:8000` | Used Docker internal URL in `VITE_API_URL` | Use public HTTPS URL |
| Blank page or broken CSS/JS | Missing `base: '/digifile/'` in Vite | Set `base` in `vite.config.js` and rebuild |
| 404 on refresh under `/digifile/` | Missing `basename` or nginx `try_files` | Set `basename="/digifile"`; check Section 7.1 nginx |
| Media/PDF 404 | nginx not proxying `/digifile/media/` | Add `/digifile/media/` location block |
| Backup database fails | `mysqldump` missing or DB unreachable | Rebuild backend image; check `DB_HOST=db` |
| Email links go to localhost | `FRONTEND_URL` still dev value | Set `https://apps.cmu.edu.ph/digifile` in `backend/.env` |

---

## 12. Security notes

- Never commit `backend/.env` or `frontend/.env` with real secrets.
- Keep `DEBUG=False` in production.
- Consider restricting CORS in `backend/config/settings.py` to `https://apps.cmu.edu.ph` instead of `CORS_ALLOW_ALL_ORIGINS = True` for production hardening.
- Expose backend port only on localhost; public traffic should go through Vesta nginx with SSL.
- Restrict server SSH and Vesta admin access.

---

*Last updated for DFS V2 — CMU production at apps.cmu.edu.ph/digifile, backup module, split env files, MySQL via Docker.*

