# Vesta Deployment Guide

Production deployment guide for **Digitized Filing System (DFS)** on a server using **Vesta CP**, **nginx**, and **Docker**.

> **Related:** [DOCKER_SETUP.md](../DOCKER_SETUP.md) (local dev) · [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) · [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

**Start here for your domain:** [Section 2 — What to change (your URL, not localhost)](#2-what-to-change--your-url-not-localhost)

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

```text
Browser
   │
   ▼
Vesta nginx (host) ──► /              → frontend/dist (static SPA)
                   ──► /api/, /media/ → backend container :8000
                   ──► /admin/        → backend container (optional)

backend container ──► mysql container (DB_HOST=db)
```

### Local dev vs production

| | Local (`docker compose`) | Production (Vesta) |
|--|---------------------------|---------------------|
| Frontend | Vite dev server in Docker (:5173) | Static `dist/` on nginx |
| Backend | `runserver` (development only) | **Gunicorn** (recommended) |
| Database | MySQL container | MySQL container (or managed DB) |
| Public URL | `localhost` | Your domain + SSL (Vesta) |
| Env files | `backend/.env`, `frontend/.env` | Same split; **production values** |

---

## 2. What to change — your URL (not localhost)

Use this section as a checklist when moving from local dev to Vesta. Replace example domains with **your real domain** (e.g. `https://digifile.yourschool.edu`).

### 2.1 Quick rule

| Who sees it | Use |
|-------------|-----|
| **Users in the browser** | `https://your-domain.edu` (no `localhost`, no `:5173`, no public `:8000`) |
| **Email links** (reset password, activation) | Same public frontend URL |
| **Server internal only** (nginx → Docker) | `127.0.0.1:8000` is OK — users never type this |

```text
User browser     →  https://digifile.yourschool.edu
Email links      →  https://digifile.yourschool.edu/set-password/...
nginx (internal) →  http://127.0.0.1:8000  (backend container)
MySQL (internal) →  DB_HOST=db  (Docker service name)
```

---

### 2.2 Files you **must** change for production

#### A) `frontend/.env` — on your **build machine** (before `npm run build`)

| Variable | Dev (do not deploy) | Production (your URL) |
|----------|---------------------|------------------------|
| `VITE_API_URL` | `http://localhost:8000` | `https://digifile.yourschool.edu` |

**Same-domain setup (recommended):** API is at `https://your-domain/api/...` on the same host as the SPA.

```env
# frontend/.env — example production
VITE_API_URL=https://digifile.yourschool.edu
```

**Subdomain setup:** API on a separate host.

```env
VITE_API_URL=https://api.digifile.yourschool.edu
```

After editing:

```bash
cd frontend
npm run build
```

Upload **`frontend/dist/`** to Vesta `public_html`. The old `dist/` built with `localhost` will still call localhost — you must rebuild.

> **Do not** put `frontend/.env` on the Vesta web root. Only upload `dist/` contents.

---

#### B) `backend/.env` — on the **Vesta server** (loaded by Docker backend container)

Create from `backend/.env.example`. **Never commit** this file to Git.

| Variable | Dev example | Change to (production) |
|----------|-------------|-------------------------|
| `DEBUG` | `True` | **`False`** |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,backend` | **`digifile.yourschool.edu`** (your domain only; see note below) |
| `FRONTEND_URL` | `http://localhost:5173` | **`https://digifile.yourschool.edu`** |
| `DJANGO_SECRET_KEY` | dev placeholder | **long random secret** |
| `DB_PASSWORD` | dev password | **strong production password** |
| `DB_HOST` | `db` | **`db`** (keep — Docker MySQL service name) |
| `DB_ENGINE` | `mysql` | **`mysql`** (keep) |
| `EMAIL_*` | test / empty | **real SMTP** for activation & reset emails |

Example production `backend/.env`:

```env
DJANGO_SECRET_KEY=replace-with-long-random-secret
DEBUG=False
ALLOWED_HOSTS=digifile.yourschool.edu

DB_ENGINE=mysql
DB_NAME=dfs_project
DB_USER=dfs_user
DB_PASSWORD=your-strong-db-password
DB_HOST=db
DB_PORT=3306

FRONTEND_URL=https://digifile.yourschool.edu

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=your_email@gmail.com
```

**`ALLOWED_HOSTS` note:** List the hostname(s) users type in the browser (no `https://`, no path). If you use both `www` and non-`www`, list both:

```env
ALLOWED_HOSTS=digifile.yourschool.edu,www.digifile.yourschool.edu
```

Optional: keep `127.0.0.1` only if you run health checks on the server with `curl http://127.0.0.1:8000/...`. It is **not** your public URL.

---

#### C) Vesta CP — nginx / domain (server panel, not a repo file)

| Where in Vesta | What to set |
|----------------|-------------|
| **Web → Add Domain** | Your domain, e.g. `digifile.yourschool.edu` |
| **SSL** | Enable Let's Encrypt / certificate |
| **Document root** | Point to folder where you uploaded `dist/` (e.g. `public_html`) |
| **Nginx custom config** | Proxy `/api/` and `/media/` to backend (Section 7) |

Replace every `dfs.example.com` in nginx examples with **your domain path**, e.g.:

```nginx
root /home/admin/web/digifile.yourschool.edu/public_html;
```

---

### 2.3 Files you usually **do not** change for URL

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

### 2.4 Source code fallbacks (no edit needed if `.env` is correct)

Some pages default to `127.0.0.1:8000` **only when `VITE_API_URL` is missing**:

- `frontend/src/lib/api.ts`
- `frontend/src/lib/backup.ts`
- `frontend/src/pages/auditlogs/AuditLogsPage.tsx`
- `frontend/src/pages/documents/DocumentsPage.tsx`

If you build with the correct `frontend/.env`, production `dist/` will **not** use localhost. No source changes required.

---

### 2.5 Side-by-side example (same domain)

Assume public site: **`https://digifile.yourschool.edu`**

| Setting | Wrong (dev left in prod) | Correct (production) |
|---------|--------------------------|----------------------|
| User opens app | `http://localhost:5173` | `https://digifile.yourschool.edu` |
| `frontend/.env` → `VITE_API_URL` | `http://localhost:8000` | `https://digifile.yourschool.edu` |
| `backend/.env` → `FRONTEND_URL` | `http://localhost:5173` | `https://digifile.yourschool.edu` |
| `backend/.env` → `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `digifile.yourschool.edu` |
| Password email link | `http://localhost:5173/reset-password/...` | `https://digifile.yourschool.edu/reset-password/...` |
| API from browser | `http://localhost:8000/api/...` | `https://digifile.yourschool.edu/api/...` |
| nginx → backend (internal) | — | `http://127.0.0.1:8000` ✓ |

---

### 2.6 Side-by-side example (API subdomain)

| Setting | Value |
|---------|--------|
| SPA URL | `https://digifile.yourschool.edu` |
| API URL | `https://api.digifile.yourschool.edu` |
| `VITE_API_URL` | `https://api.digifile.yourschool.edu` |
| `FRONTEND_URL` | `https://digifile.yourschool.edu` |
| `ALLOWED_HOSTS` | `api.digifile.yourschool.edu,digifile.yourschool.edu` |

---

### 2.7 Common mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Built `dist/` without updating `frontend/.env` | API calls go to `localhost:8000` | Rebuild frontend with production `VITE_API_URL` |
| `FRONTEND_URL` still `localhost:5173` | Email links open localhost | Set `FRONTEND_URL` in `backend/.env` |
| Domain missing from `ALLOWED_HOSTS` | **400 Disallowed Host** | Add your domain to `ALLOWED_HOSTS` |
| `VITE_API_URL=http://backend:8000` | API fails in browser | Use public HTTPS domain |
| Users open `:8000` directly | Bypasses nginx / SSL | Use domain only; keep 8000 internal |
| Uploaded old `dist/` after env change | Still broken until rebuild | Always rebuild after `VITE_API_URL` change |

---

### 2.8 Deployment order (recommended)

1. Create Vesta domain + SSL  
2. Write **`backend/.env`** on server with production domain, `DEBUG=False`, secrets  
3. Start Docker (`db` + `backend`)  
4. Write **`frontend/.env`** on build machine with `VITE_API_URL`  
5. Run **`npm run build`**  
6. Upload **`dist/`** to Vesta `public_html`  
7. Configure **nginx** proxy for `/api/` and `/media/`  
8. Smoke test: login, upload, password reset email link  

---

## 3. Prerequisites

On the Vesta server:

- Docker and Docker Compose installed
- Vesta CP domain configured (SSL certificate recommended)
- Git access to the DFS repository (or deploy artifacts)
- Node.js on a build machine (your PC or CI) to run `npm run build`, **or** build `dist/` locally and upload it

---

## 4. Environment files

DFS uses **separate env files** for backend and frontend. Do not commit real secrets.

### 4.1 Frontend (build time)

File: `frontend/.env`

```env
VITE_API_URL=https://your-dfs-domain.example.com
```

**Important:**

- Set this to the URL the **browser** uses to reach the API.
- If nginx proxies `/api` on the **same domain** as the SPA, use that domain (e.g. `https://dfs.example.com`).
- If the API is on a subdomain, use that (e.g. `https://api.dfs.example.com`).
- Do **not** use Docker-internal names like `http://backend:8000` — browsers cannot resolve them.
- Rebuild after any change: `npm run build` (Vite bakes this into `dist/`).

### 4.2 Backend (runtime, inside container)

File: `backend/.env`

```env
DJANGO_SECRET_KEY=<long-random-secret>
DEBUG=False
ALLOWED_HOSTS=dfs.example.com,api.dfs.example.com,127.0.0.1

DB_ENGINE=mysql
DB_NAME=dfs_project
DB_USER=dfs_user
DB_PASSWORD=<strong-password>
DB_HOST=db
DB_PORT=3306

FRONTEND_URL=https://dfs.example.com

EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<smtp-user>
EMAIL_HOST_PASSWORD=<smtp-password>
DEFAULT_FROM_EMAIL=noreply@example.com

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
cp .env.example .env
# Edit .env — set VITE_API_URL to production API URL
npm ci
npm run build
```

Output: `frontend/dist/` (HTML, JS, CSS, assets).

### 5.2 Upload to Vesta

Copy the contents of `dist/` to the domain web root, for example:

```text
/home/admin/web/dfs.example.com/public_html/
```

Vesta nginx should serve this directory for the site. The React app uses client-side routing, so nginx must fall back to `index.html` for unknown paths (see Section 8).

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

Add custom nginx rules for the DFS domain in Vesta ( **Web → domain → Edit → Advanced** or custom template). Adjust paths and upstream to match your server.

### 7.1 Same-domain layout (recommended)

SPA and API on `https://dfs.example.com`:

```nginx
# React SPA — static files from Vesta public_html
location / {
    root /home/admin/web/dfs.example.com/public_html;
    try_files $uri $uri/ /index.html;
}

# Django API
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Uploaded files (PDFs, profile pictures)
location /media/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Optional: Django admin
location /admin/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

With this layout:

```env
# frontend/.env at build time
VITE_API_URL=https://dfs.example.com

# backend/.env
ALLOWED_HOSTS=dfs.example.com,127.0.0.1
FRONTEND_URL=https://dfs.example.com
```

### 7.2 Subdomain layout (alternative)

| URL | Purpose |
|-----|---------|
| `https://dfs.example.com` | Static SPA |
| `https://api.dfs.example.com` | Backend API |

- Build frontend with `VITE_API_URL=https://api.dfs.example.com`
- Set `ALLOWED_HOSTS=api.dfs.example.com,dfs.example.com`
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
- [ ] `ALLOWED_HOSTS` includes production domain(s)
- [ ] `FRONTEND_URL` matches public frontend URL (email links)
- [ ] `VITE_API_URL` set correctly; frontend rebuilt and `dist/` uploaded
- [ ] Backend uses Gunicorn, not `runserver`
- [ ] Backend bound to `127.0.0.1:8000` (or internal network only)
- [ ] SSL enabled in Vesta for the domain
- [ ] Migrations applied; admin user created
- [ ] SMTP configured for activation / password reset emails
- [ ] `backend_media` and `mysql_data` volumes backed up (or use Backup Management UI)

### Smoke test

- [ ] Login at production URL
- [ ] Upload a PDF
- [ ] Download a document
- [ ] Admin: Backup Management downloads (database + media)
- [ ] Password reset email link opens correct frontend URL

---

## 10. Updates and rollbacks

### Frontend update

```bash
# On build machine
cd frontend && npm run build
# Upload new dist/ to public_html (replace old files)
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
| **400 DisallowedHost** | Domain missing from `ALLOWED_HOSTS` | Add production domain to `backend/.env` |
| API calls fail / CORS | Wrong `VITE_API_URL` | Rebuild frontend with correct public API URL |
| API calls go to `backend:8000` | Used Docker internal URL in `VITE_API_URL` | Use public domain nginx exposes |
| Blank page on refresh | nginx missing SPA fallback | Add `try_files ... /index.html` |
| Media/PDF 404 | nginx not proxying `/media/` | Add `/media/` location block |
| Backup database fails | `mysqldump` missing or DB unreachable | Rebuild backend image; check `DB_HOST=db` |
| Email links go to localhost | `FRONTEND_URL` still dev value | Set production URL in `backend/.env` |

---

## 12. Security notes

- Never commit `backend/.env` or `frontend/.env` with real secrets.
- Keep `DEBUG=False` in production.
- Consider restricting CORS in `backend/config/settings.py` to your frontend domain instead of `CORS_ALLOW_ALL_ORIGINS = True` for production hardening.
- Expose backend port only on localhost; public traffic should go through Vesta nginx with SSL.
- Restrict server SSH and Vesta admin access.

---

*Last updated for DFS V2 — backup module, split env files, MySQL via Docker.*
