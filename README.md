# NutriGenie

<p align="center">
  <strong>English</strong> · <a href="README.zh-CN.md">简体中文</a>
</p>

<div align="center">
  <p><strong>AI-powered personalized nutrition planning with deterministic validation</strong></p>
  <p>
    <img alt="Vue 3" src="https://img.shields.io/badge/Vue-3-42b883?logo=vuedotjs&logoColor=white">
    <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-6-3178c6?logo=typescript&logoColor=white">
    <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white">
    <img alt="Python" src="https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white">
    <img alt="MySQL" src="https://img.shields.io/badge/MySQL-8.0+-4479a1?logo=mysql&logoColor=white">
  </p>
</div>

NutriGenie creates personalized weekly meal plans from a user's health goals, body metrics, budget, dietary preferences, allergies, restrictions, and available ingredients. The language model interprets requirements and creates candidate recipes, while deterministic application logic standardizes ingredients, recalculates nutrition and cost, enforces hard constraints, optimizes the weekly schedule, and persists validated results.

> NutriGenie provides general meal-planning information only. It is not medical advice, a diagnosis, a treatment recommendation, or a professional nutrition prescription.

## Interface Preview

| Home | Plan Workspace |
| --- | --- |
| ![NutriGenie home page](screenshots/home.png) | ![NutriGenie plan workspace](screenshots/plan-result.png) |

### Sign Up and Sign In

![NutriGenie authentication page](screenshots/auth.png)

## Features

- **Accounts and nutrition profiles** — Sign up, sign in, and manage body metrics, activity level, health goals, diet type, budget, allergies, and food restrictions.
- **Natural-language planning** — Describe requirements in everyday language and convert them into structured constraints for personalized meal generation.
- **Deterministic fact calculation** — Map every ingredient to a standard catalog and recalculate nutrition and cost instead of trusting model estimates.
- **Hard-constraint validation and repair** — Check allergies, restrictions, diet type, ingredient resolution, and output structure, with a limited number of targeted repair attempts.
- **Weekly plan optimization** — Control recipe repetition, adjacent duplicates, and overall variety while calibrating trusted ingredient portions against plan targets.
- **Iterative updates and version history** — Refine an existing plan in natural language. Every successful update creates a separate version, while failed updates leave the last valid version intact.
- **Execution and shopping support** — Track today's meals and completion state, review nutrition and budget summaries, and use an ingredient-level shopping list.
- **Administration** — Manage the standard ingredient catalog, nutrition facts, and recipes through role-protected admin pages.
- **Responsive and accessible UX** — Support desktop and mobile layouts, keyboard navigation, visible focus, 200% zoom reflow, and reduced-motion preferences.

## How It Works

```text
Nutrition profile + natural-language request
                    │
                    ▼
        Intent parsing and constraint compilation
                    │
                    ▼
          Language model creates candidates
                    │
                    ▼
 Ingredient normalization and nutrition/cost recalculation
                    │
                    ▼
      Hard validation and limited targeted repair
                    │
                    ▼
 Weekly optimization, portion calibration, final validation
                    │
                    ▼
 Nutrition report, shopping list, and immutable version
```

NutriGenie follows a simple rule: the model creates; the application verifies. Model output must pass the standard ingredient catalog and deterministic validation pipeline before it can become a final plan. If validation still fails after repair attempts, the workflow returns an explicit failure instead of silently saving an invalid result.

## Technology Stack

| Layer | Technologies |
| --- | --- |
| Frontend | Vue 3, TypeScript, Vite, Element Plus, Pinia, ECharts |
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic |
| AI workflow | LangGraph, LangChain, structured model output |
| Database | MySQL; SQLite is supported for a quick local setup |
| Authentication | JWT, Argon2 password hashing, role-based admin access |
| Testing | Pytest, Node.js Test Runner, Vue Type Check, Vite Build |

## Project Structure

```text
NutriGenie/
├─ backend/
│  ├─ alembic/             # Database migrations
│  ├─ app/
│  │  ├─ api/              # REST endpoints and request/response schemas
│  │  ├─ db/               # Database connection, verification, and seed data
│  │  ├─ models/           # SQLAlchemy models
│  │  ├─ services/         # Nutrition, cost, constraint, and planning services
│  │  ├─ tasks/            # Plan-generation tasks
│  │  └─ workflow/         # LangGraph workflow and prompts
│  ├─ scripts/             # Setup, admin, and acceptance scripts
│  ├─ tests/               # Unit and integration tests
│  ├─ .env.example         # Backend environment template
│  └─ requirements.txt
├─ frontend/
│  ├─ public/              # Static assets
│  ├─ src/
│  │  ├─ api/              # API client modules
│  │  ├─ components/       # Shared, layout, recipe, and plan components
│  │  ├─ repositories/     # Local state persistence
│  │  ├─ router/           # Routes and access guards
│  │  ├─ stores/           # Pinia stores
│  │  └─ views/            # Application pages
│  ├─ tests/               # Frontend contract tests
│  └─ package.json
├─ screenshots/            # README screenshots
├─ README.md               # English
└─ README.zh-CN.md         # Simplified Chinese
```

## Quick Start

### Requirements

- Python 3.11 or later
- Node.js 20 or later
- MySQL 8.0 or later; SQLite is also supported for a quick local setup
- A valid DeepSeek API key

### 1. Configure the Backend

The following examples use PowerShell:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

For a quick SQLite setup, edit `backend/.env` and provide at least:

```dotenv
DATABASE_URL_OVERRIDE=sqlite:///./data/nutrigenie.db
LLM_API_KEY=your-deepseek-api-key
JWT_SECRET_KEY=replace-with-a-long-random-secret
DEV_EMAIL_VERIFICATION_CODE=123456
```

To use MySQL, leave `DATABASE_URL_OVERRIDE` empty and configure:

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=nutrigenie
```

Create the database before running the migrations:

```sql
CREATE DATABASE nutrigenie
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 2. Initialize and Start the API

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade heads
python -m app.db.seed
python -m uvicorn app.main:app --reload --port 8000
```

Once the server is running:

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>

### 3. Start the Frontend

Open another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

The frontend runs at <http://localhost:5173> by default. During development, Vite proxies `/api` requests to <http://localhost:8000>.

### 4. Create an Admin Account (Optional)

Add the following values to `backend/.env`:

```dotenv
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=replace-with-a-strong-password
ADMIN_NICKNAME=Administrator
```

Then run:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m scripts.create_admin
```

## Testing

### Backend

Run the default test suite:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest tests -q
```

Run the MySQL integration tests:

```powershell
python -m pytest tests -m integration -q
```

Validate the complete meal-plan workflow against a real model and MySQL:

```powershell
python scripts\smoke_ai_native_v2.py --synthetic --timeout 480
```

The acceptance script uses a synthetic profile only and removes its temporary records after the run.

### Frontend

```powershell
cd frontend
npm test
npm run build
```

## Security

- Never commit `backend/.env`, API keys, database passwords, JWT secrets, or admin credentials.
- Use a strong random JWT secret in deployed environments and replace the local verification-code mechanism.
- Keep API keys in backend environment variables only; never include them in frontend code or build artifacts.
- Before exposing the application publicly, disable debug mode, restrict CORS origins, and add monitoring and access controls for the API, database, and task execution.
- Nutrition and price data vary by brand, origin, cooking loss, and region. Review generated results against real-world conditions.

## Contributing

Issues and focused improvements are welcome. Before opening a pull request:

1. Keep the change set focused and include relevant tests.
2. Ensure backend tests, frontend tests, and the production build pass.
3. Do not include secrets, real user data, or locally generated files.

## License

This repository does not currently include an open-source license. No permission to copy, modify, or distribute the code is granted unless explicitly stated.
