# React (Frontend) — Installation Process (Cheat Sheet)

This doc is written to match this repo’s frontend folder: `project_dfs/frontend/`.

## What you get in this frontend

- **Build tool**: Vite (`npm run dev`)
- **Framework**: React 19
- **Routing**: `react-router-dom`
- **HTTP**: `axios`
- **Auth helper**: `jwt-decode`
- **UI**: Tailwind CSS v4 + shadcn tooling + Radix-based components
- **Aliases**: `@` resolves to `frontend/src` (see `vite.config.js`)

## Prerequisites (IMPORTANT for Vite 7)

- **Node.js**: **20.19+** (or **22.12+**)  
  Vite 7 dropped Node 18 support.
- **npm**: comes with Node (this repo uses **npm** because `package-lock.json` exists)

## Dependencies used (from `frontend/package.json`)

### Runtime dependencies

- `react`, `react-dom`
- `react-router-dom`
- `axios`
- `jwt-decode`
- `recharts`
- UI helpers: `clsx`, `tailwind-merge`, `class-variance-authority`, `tw-animate-css`
- icons/fonts: `lucide-react`, `@fontsource-variable/inter`

### Dev dependencies

- Vite + React plugin: `vite`, `@vitejs/plugin-react`
- Tailwind toolchain: `tailwindcss`, `postcss`, `autoprefixer`, `@tailwindcss/postcss`
- Linting: `eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `@eslint/js`, `globals`
- shadcn tooling: `shadcn`

## Run THIS repo (copy/paste)

Open **PowerShell** at the repo root (`project_dfs/`).

### 0) Environment variables (API base URL)

This repo uses a Vite env var in `frontend/.env`:

```
VITE_API_URL=http://localhost:8000
```

### 1) Install packages

```powershell
cd "d:\4th Year\SDD OJT\project_dfs\frontend"
npm install
```

### 2) Start the dev server

```powershell
npm run dev
```

Vite will print the local URL, typically:

- Frontend: `http://localhost:5173/`

## Run backend + frontend together (quick routine)

### Terminal 1 (backend)

```powershell
cd "d:\4th Year\SDD OJT\project_dfs\backend"
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

### Terminal 2 (frontend)

```powershell
cd "d:\4th Year\SDD OJT\project_dfs\frontend"
npm run dev
```

Backend default:

- `http://127.0.0.1:8000/`

Your frontend should call the backend API using that base URL (or whatever you configure).

## Create a NEW React frontend like this (Vite template steps)

From a new empty folder:

```powershell
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm run dev
```

To match this repo’s style (high-level checklist):

- Add routing: `npm i react-router-dom`
- Add HTTP client: `npm i axios`
- Add JWT helper: `npm i jwt-decode`
- Add Tailwind v4 + PostCSS (follow Tailwind v4 docs)
- Set Vite alias `@ -> ./src` in `vite.config.js`
- If using shadcn components, initialize shadcn config in the project and add components through the shadcn workflow you prefer

## Common issues

- **`vite` / dev server fails on Node 18**
  - Upgrade Node to 20.19+ (or 22.12+).
- **CORS error when calling Django**
  - Backend needs CORS configured. In this repo it’s permissive for dev.
- **`@/` import not found**
  - This repo uses `@` alias in `vite.config.js`. If you recreate the project, add the alias again.




## Optional React Grab Dev Tool

To enable the React Grab MCP client in development, place this inside `frontend/index.html`:

```html
<!-- React Grab MCP Client for the small dev overlay in the top-right corner. -->
<script type="module">
  if (import.meta.env.DEV) {
    import("react-grab");
    import("@react-grab/mcp/client");
  }
</script>
```
