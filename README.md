# Digitized Filing System (DFS)

**DigiFile** — the official document management system of **Central Mindanao University (CMU)**.

Django REST + React/Vite application for OrgUnit-scoped PDF document management.

## Developer documentation

| Document | Description |
|----------|-------------|
| [docs/HANDOFF.md](docs/HANDOFF.md) | August 2026 schema/Docker handoff (table naming, MySQL 8.4) |
| [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Architecture, access control, database table naming, onboarding |
| [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) | Full REST API reference |
| [docs/FRONTEND_ROUTES.md](docs/FRONTEND_ROUTES.md) | React route map and role guards |
| [DOCKER_SETUP.md](DOCKER_SETUP.md) | Local dev (`docker-compose.dev.yml`) / Docker setup |
| [docs/DATA_MIGRATION_POLICY.md](docs/DATA_MIGRATION_POLICY.md) | Ongoing data rules: document codes, employee numbers, requisitioners |
| [docs/ALPHA_TEST_CHECKLIST.md](docs/ALPHA_TEST_CHECKLIST.md) | Manual alpha sign-off checklist |
| [docs/VESTA_DEPLOYMENT.md](docs/VESTA_DEPLOYMENT.md) | Production deploy on Vesta CP + nginx |
| [docs/VPAA_PRESENTATION_GUIDE.md](docs/VPAA_PRESENTATION_GUIDE.md) | CMU demo script and module walkthrough |
| [CHATBOT_CAPABILITIES.md](CHATBOT_CAPABILITIES.md) | Document Assistant features |
| Live API docs | `http://localhost:8000/api/docs/` (Swagger, after backend start) |

## Stack

- **Backend:** Django, Django REST Framework, JWT
- **Frontend:** React, Vite, TypeScript, shadcn/ui
