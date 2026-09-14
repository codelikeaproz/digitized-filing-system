# Digitized Filing System (DFS)

**DigiFile** — the official document management system of **Central Mindanao University (CMU)**.

Django REST + React/Vite application for OrgUnit-scoped PDF document management.

## Developer documentation

| Document | Description |
|----------|-------------|
| [docs/DigiFile Vault Memory/HANDOFF.md](docs/DigiFile%20Vault%20Memory/HANDOFF.md) | August 2026 schema/Docker handoff (table naming, MySQL 8.4) |
| [docs/DigiFile Vault Memory/DEVELOPER_GUIDE.md](docs/DigiFile%20Vault%20Memory/DEVELOPER_GUIDE.md) | Architecture, access control, database table naming, onboarding |
| [docs/DigiFile Vault Memory/API_DOCUMENTATION.md](docs/DigiFile%20Vault%20Memory/API_DOCUMENTATION.md) | Full REST API reference |
| [docs/DigiFile Vault Memory/FRONTEND_ROUTES.md](docs/DigiFile%20Vault%20Memory/FRONTEND_ROUTES.md) | React route map and role guards |
| [DOCKER_SETUP.md](DOCKER_SETUP.md) | Local dev (`docker-compose.dev.yml`) / Docker setup |
| [docs/DigiFile Vault Memory/DATA_MIGRATION_POLICY.md](docs/DigiFile%20Vault%20Memory/DATA_MIGRATION_POLICY.md) | Ongoing data rules: document codes, employee numbers, requisitioners |
| [docs/DigiFile Vault Memory/ALPHA_TEST_CHECKLIST.md](docs/DigiFile%20Vault%20Memory/ALPHA_TEST_CHECKLIST.md) | Manual alpha sign-off checklist |
| [docs/DigiFile Vault Memory/VESTA_DEPLOYMENT.md](docs/DigiFile%20Vault%20Memory/VESTA_DEPLOYMENT.md) | Production deploy on Vesta CP + nginx |
| [docs/DigiFile Vault Memory/VPAA_PRESENTATION_GUIDE.md](docs/DigiFile%20Vault%20Memory/VPAA_PRESENTATION_GUIDE.md) | CMU demo script and module walkthrough |
| [CHATBOT_CAPABILITIES.md](CHATBOT_CAPABILITIES.md) | Document Assistant features |
| Live API docs | `http://localhost:8000/api/docs/` (Swagger, after backend start) |

## Stack

- **Backend:** Django, Django REST Framework, JWT
- **Frontend:** React, Vite, TypeScript, shadcn/ui
