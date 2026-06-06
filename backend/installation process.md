# Django (Backend) — Installation Process (Cheat Sheet)

This doc is written to match this repo’s backend folder: `project_dfs/backend/`.

## What you get in this backend

- **Framework**: Django (project settings module: `config.settings`)
- **API**: Django REST Framework (DRF)
- **Auth**: SimpleJWT (`/api/token/`, `/api/token/refresh/`)
- **User model**: Custom user model (`AUTH_USER_MODEL = "accounts.User"`)
- **CORS**: `django-cors-headers` (currently allows all origins in dev)
- **DB**: **SQLite** by default (even though `psycopg2-binary` is installed)

## Prerequisites (Windows)

- **Python**: 3.10+ (recommended 3.11+)
- **pip**: comes with Python
- Optional: **PostgreSQL** (only if you switch DB config from SQLite)

## Dependencies used (from `backend/requirements.txt`)

- `Django`
- `djangorestframework`
- `djangorestframework-simplejwt`
- `django-cors-headers`
- `python-dotenv`
- `psycopg2-binary` (Postgres driver; optional unless you use Postgres)
- plus transitive/related libs: `asgiref`, `PyJWT`, `pytz`, `sqlparse`

> Tip: your `requirements.txt` is **not pinned** (no versions). For reproducible installs, see “Pin versions” below.

## Run THIS repo (copy/paste)

Open **PowerShell** at the repo root (`project_dfs/`).

### 1) Create + activate a virtual environment

```powershell
cd "d:\4th Year\SDD OJT\project_dfs\backend"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If activation is blocked:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 2) Install Python packages

```powershell
pip install -r requirements.txt
```

### 3) Migrate DB + create admin user

```powershell
python manage.py migrate
python manage.py createsuperuser
```

### 4) Run the Django dev server

```powershell
python manage.py runserver
```

Default dev URL:

- Backend: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

## Docker Dev Reset (MySQL)

Use this only for local development when records are dummy/test data. This deletes the Docker MySQL volume and recreates all tables from the current clean migrations.

From the repo root:

```powershell
docker compose down -v
docker compose up --build
```

Wait until backend logs show:

```text
Waiting for MySQL...
Applying migrations...
Starting development server at http://0.0.0.0:8000/
```

Then create the first admin account (same as [DOCKER_SETUP.md](../DOCKER_SETUP.md)):

```powershell
docker compose exec backend python manage.py createsuperuser
```

Use your email as the login. Superusers get role `admin`; leave Org Unit empty.

Open:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Django admin: `http://localhost:8000/admin/`

Do not run `docker compose down -v` if you need to keep real records.

## API endpoints (from `backend/config/urls.py`)

- **Register**: `POST /api/user/register`
- **Login (JWT)**: `POST /api/token/`
- **Refresh token**: `POST /api/token/refresh/`
- **DRF session login**: `GET /api-auth/`

## Typical request bodies (example)

### JWT login

```json
{ "username": "your_user", "password": "your_pass" }
```

Response includes `access` and `refresh`.

### Auth header for protected APIs

```
Authorization: Bearer <access_token>
```

## Environment variables / `.env`

This repo loads environment variables via `python-dotenv` in `config/settings.py` (`load_dotenv()`), but there is **no `.env` committed** right now.

Recommended (for future projects):

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG` (`True/False`)
- `DATABASE_URL` or `DB_*` variables (if using Postgres)
- `CORS_ALLOWED_ORIGINS` (instead of allow-all)

## Pin versions (recommended for “create another project”)

If you want reproducible installs, do this once after installing:

```powershell
pip freeze > requirements.lock.txt
```

Then in future installs:

```powershell
pip install -r requirements.lock.txt
```

## Create a NEW Django backend like this (template steps)

From a new empty folder:

```powershell
mkdir backend
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install Django djangorestframework djangorestframework-simplejwt django-cors-headers python-dotenv psycopg2-binary
django-admin startproject config .
python manage.py startapp accounts
```

Then update `config/settings.py` (high-level checklist):

- Add to `INSTALLED_APPS`:
  - `rest_framework`
  - `corsheaders`
  - `accounts`
- Add CORS middleware
- Set `AUTH_USER_MODEL = "accounts.User"` (and implement your custom user model)
- Configure DRF + SimpleJWT
- Configure DB (SQLite or Postgres)

Finally:

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

## Common issues

- **`ModuleNotFoundError: No module named 'django'`**
  - You forgot to activate `.venv`, or installed packages globally.
- **Powershell can’t activate venv**
  - Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **JWT login returns 401**
  - Check username/password. Also ensure you’re calling `POST /api/token/` with JSON body.
- **CORS errors from React**
  - In this repo dev is permissive (`CORS_ALLOW_ALL_ORIGINS = True`). For production, lock it down.

