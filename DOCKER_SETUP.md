# Docker Setup Guide

This guide runs the Digitized Filing System with Docker and explains how to switch the backend database from SQLite to MySQL safely.

## Project Services

- `backend`: Django + Django REST Framework on `http://localhost:8000`
- `frontend`: React + Vite on `http://localhost:5173`
- `db`: MySQL 8 database on host port `3307`
- `backend_media`: Docker volume for uploaded files
- `frontend_node_modules`: Docker volume for frontend dependencies

## 1. First-Time Setup

Create separate environment files for backend and frontend:

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

Edit `backend/.env` and set real Django values:

```env
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,backend

EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
DEFAULT_FROM_EMAIL=your_email@gmail.com
```

Edit `frontend/.env` for Vite variables:

```env
VITE_API_URL=http://localhost:8000
```

Do not commit `.env` files. They contain secrets. Do not use a shared root-level `.env`.

## 2. Run With MySQL

MySQL is the default Docker database.

In `backend/.env`:

```env
DB_ENGINE=mysql
DB_NAME=vpaa_digi_file
DB_USER=dfs_user
DB_PASSWORD=dfs_password
DB_HOST=db
DB_PORT=3306
MYSQL_ROOT_PASSWORD=root_password
MYSQL_HOST_PORT=3307
```

Build and run:

```powershell
docker compose up --build
```

The backend waits for MySQL, runs migrations automatically, then starts Django.

Expected backend logs:

```text
Waiting for MySQL...
Applying migrations...
Starting development server at http://0.0.0.0:8000/
```

Open:

```text
Frontend: http://localhost:5173
Backend:  http://localhost:8000
MySQL:    localhost:3307
```

**Backup Management (admin only):** The backend image includes `default-mysql-client` so database backups can run `mysqldump` against the MySQL container. Use **Administration → Backup Management** in the UI or `GET /api/backups/database` and `GET /api/backups/media` with a JWT.

### Create the first admin account

Migrations do **not** create a login user. After the stack is up, run once:

```powershell
docker compose exec backend python manage.py createsuperuser
```

- **Email:** your admin login (for example `admin@dfs.local`)
- **Password:** choose a strong password when prompted
- **Role:** set automatically to `admin` for superusers
- **Org Unit:** leave empty (global admin)

Use this account to sign in at `http://localhost:5173`.

## 3. Clean First Run

If you want a fresh MySQL database volume (for example after migration squashes or to wipe test data):

```powershell
docker compose down -v
docker compose up --build
```

This deletes Docker volumes, including the MySQL database. Do not run it if you need to keep data.

Then create the first admin account as described in **Create the first admin account** above.

## 4. Wait-For-MySQL Logic

The backend uses `nc` to wait until the MySQL port is reachable:

```yaml
command: >
  sh -c "
  until nc -z db 3306; do
    echo 'Waiting for MySQL...';
    sleep 2;
  done;
  echo 'Applying migrations...';
  python manage.py migrate &&
  python manage.py runserver 0.0.0.0:8000
  "
```

`depends_on` only controls startup order. It does not mean MySQL is ready to accept connections. The `nc` loop prevents Django from crashing with connection refused errors.

## 5. Useful Docker Commands

Stop containers:

```powershell
docker compose down
```

Restart after code changes:

```powershell
docker compose up
```

Rebuild after dependency changes:

```powershell
docker compose build
docker compose up
```

View logs:

```powershell
docker compose logs -f backend
docker compose logs -f frontend
```

Open Django shell:

```powershell
docker compose exec backend python manage.py shell
```

## 6. SQLite Alternative

SQLite is still supported by the Django settings, but the provided Docker Compose file is MySQL-first.

For local non-Docker development, use:

```env
DB_ENGINE=sqlite
SQLITE_NAME=backend/db.sqlite3
```

Then run Django outside Docker:

```powershell
cd backend
python manage.py migrate
python manage.py runserver
```

## 7. Preserve Existing SQLite Data Before Switching

If you already have SQLite data and want to move it to Docker MySQL, export it before changing `.env`.

### Step 1: Export SQLite Data Outside Docker

While still using SQLite locally:

```powershell
cd backend
python manage.py dumpdata --exclude auth.permission --exclude contenttypes --indent 2 -o data.json
```

This creates:

```text
backend/data.json
```

### Step 2: Configure Docker MySQL

Update `backend/.env`:

```env
DB_ENGINE=mysql
DB_NAME=vpaa_digi_file
DB_USER=dfs_user
DB_PASSWORD=dfs_password
DB_HOST=db
DB_PORT=3306
```

### Step 3: Start Docker MySQL And Migrate

```powershell
docker compose up --build
```

### Step 4: Load Data

```powershell
docker compose exec backend python manage.py loaddata /app/data.json
```

### Step 5: Validate Data

Confirm these still work:

- Users and login
- Org Units
- Categories
- Folders
- Documents
- Audit Logs

## 8. Troubleshooting

### Docker Is Not Running

Start Docker Desktop, then run:

```powershell
docker compose up
```

### Port Already In Use

If `8000` or `5173` is already used, stop the old server or change ports in `docker-compose.yml`.

Example:

```yaml
ports:
  - "8001:8000"
```

### React Cannot Connect To Backend

Check `.env`:

```env
VITE_API_URL=http://localhost:8000
```

Then rebuild frontend:

```powershell
docker compose up --build
```

### MySQL Connection Refused

Check:

- MySQL container is running: `docker compose ps`
- `DB_HOST=db`
- `DB_PORT=3306`
- password is correct
- database credentials match the `db` service environment

Do not use this inside Docker Compose:

```env
DB_HOST=host.docker.internal
```

Use `DB_HOST=db` because `db` is the Compose service name.

### Backend Keeps Restarting Before MySQL Is Ready

Confirm the backend image has `nc`:

```powershell
docker compose run --rm backend nc -h
```

Confirm the backend command includes the wait loop:

```powershell
docker compose config
```

### Migration Errors After Pulling New Code

If migrations were squashed into `0001_initial` files (for example `notifications`), an old database may be out of sync. For local dev with disposable data:

```powershell
docker compose down -v
docker compose up --build
docker compose exec backend python manage.py createsuperuser
```

Do not use `-v` on production or when you need to keep records.

### MySQL Encoding Problems

Use `utf8mb4`:

```sql
CREATE DATABASE digitized_filing_system
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

### Missing Python Or Node Dependencies

Rebuild images:

```powershell
docker compose build --no-cache
docker compose up
```

## 9. Production Notes

- Do not use Django development server in production.
- Set `DEBUG=False`.
- Use strong `DJANGO_SECRET_KEY`.
- Restrict `ALLOWED_HOSTS`.
- Use MySQL or PostgreSQL instead of SQLite.
- Store uploaded media in persistent storage.
- Do not commit `.env`.
- Use a non-root MySQL user in production.




## 10. Optional Dev Tooling

To enable the React Grab MCP client in development, add this script inside `frontend/index.html`:

```html
<!-- React Grab MCP Client for the small dev overlay in the top-right corner. -->
<script type="module">
  if (import.meta.env.DEV) {
    import("react-grab");
    import("@react-grab/mcp/client");
  }
</script>
```
