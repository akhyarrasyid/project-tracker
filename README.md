# Project Tracker — Enterprise Task Management System

An enterprise-grade Task Management application with a decoupled architectural design. The system features a robust **FastAPI backend** (using the Repository pattern, Pydantic schemas, and SQLAlchemy models) and a highly responsive **React Vite frontend** (utilizing TailwindCSS, custom hooks, and dynamic Kanban layouts).

---

## 🏗️ Project Architecture

The codebase follows clean architecture principles, emphasizing decoupling, dependency inversion, and strict layer boundaries.

```
project-tracker/
├── backend/                       # FastAPI Backend Application
│   ├── app/
│   │   ├── api/                   # API Routing Layer
│   │   │   ├── dependencies.py    # FastAPI dependencies (DB sessions, repository instances)
│   │   │   ├── router.py          # Root APIRouter combining v1 sub-routers
│   │   │   └── v1/
│   │   │       └── task_routes.py # CRUD and bulk CSV import/template endpoints
│   │   ├── core/                  # Configuration & Global Utilities
│   │   │   ├── config.py          # Environment settings (Pydantic Settings)
│   │   │   └── exceptions.py      # Structured exception hierarchy
│   │   ├── db/                    # Data Access & Database Layer
│   │   │   ├── base.py            # SQLAlchemy Base declaration
│   │   │   ├── session.py         # SQLAlchemy engine and session factory
│   │   │   ├── models/            # SQLAlchemy Database Models (26 fields)
│   │   │   └── repositories/      # Repository Classes (Separates database logic from routes)
│   │   ├── schemas/               # Pydantic Schemas (Validation & serialization)
│   │   │   ├── common.py          # Standard paginated response envelopes
│   │   │   └── task.py            # Task validation payloads with custom invariants
│   │   ├── services/              # Business Logic & CLI Services
│   │   │   └── seed_service.py    # Idempotent database seeder script
│   │   └── main.py                # FastAPI Application Factory
│   └── tests/                     # Test Suites (Pytest)
│       ├── e2e/                   # End-to-End API endpoint tests
│       ├── integration/           # Repository and CSV task import integration tests
│       └── unit/                  # Router and service unit tests
│
├── frontend/                      # React Vite Frontend Application
│   ├── src/
│   │   ├── api/                   # Axios API service client
│   │   ├── components/            # UI Components (Kanban board, forms, CSV modal)
│   │   │   ├── ImportCsvModal.tsx # Glassmorphism CSV dropzone and upload card component
│   │   │   └── ImportCsvModal.test.tsx # CSV modal interactions and API mock tests
│   │   ├── hooks/                 # Custom React Hooks (State orchestration & API interaction)
│   │   ├── types/                 # TypeScript type interfaces matching backend schemas
│   │   └── App.tsx                # Main Dashboard View
│   └── src/App.test.tsx           # Component Integration Tests (Vitest)
│
└── docker-compose.yml             # Orchestrates multi-container local stack
```

---

## ⚡ Technology Stack

### Backend
* **FastAPI:** High-performance web framework for APIs.
* **SQLAlchemy 2.0:** Modern ORM mapping database records.
* **Pydantic v2:** Fast data validation and serialization.
* **Uv:** Ultra-fast Python package installer and runner.
* **PostgreSQL / SQLite:** Supports Postgres for production/local containers, and SQLite for lightweight local runs/testing.

### Frontend
* **React 18:** Modern UI view library.
* **Vite:** High-performance frontend bundler.
* **TailwindCSS:** Utility-first CSS styling framework.
* **Axios:** Promise-based HTTP client.
* **Vitest:** Blazing fast unit and integration testing framework.

---

## 🚀 Setup & Installation

### Local Backend Development
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Setup a virtual environment and install dependencies using `uv`:
   ```bash
   uv sync
   ```
3. Run the database migrations (Alembic or seeding script handles tables auto-creation in development):
   ```bash
   uv run python -m app.services.seed_service --seed
   ```
4. Start the FastAPI development server:
   ```bash
   uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

### Local Frontend Development
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   Open your browser at `http://localhost:5173`.

---

## 📊 Database Seeding CLI

The backend includes a feature-rich seeding CLI designed to seed **500 enterprise records** (26 fields) from `project_tracker_seed.json`.

Run the seed CLI from the `backend/` directory:
* **Seed Database (Idempotent):**
  ```bash
  uv run python -m app.services.seed_service --seed
  ```
* **Reset Database (Re-seeds all data):**
  ```bash
  uv run python -m app.services.seed_service --reset
  ```
* **Dry-Run (Validates input without saving to database):**
  ```bash
  uv run python -m app.services.seed_service --dry-run
  ```
* **Validate Only (Asserts data conformity to Pydantic schemas):**
  ```bash
  uv run python -m app.services.seed_service --validate
  ```

---

## 🧪 Running Tests & Coverage

High-quality code metrics are enforced through comprehensive unit and integration testing.

### Backend Tests (Pytest)
Run all backend tests with coverage reporting:
```bash
cd backend
uv run pytest --cov=app --cov-report=term-missing tests/
```
*Backend test coverage is maintained at **99%** overall statement coverage.*

### Frontend Tests (Vitest)
Run all frontend tests with coverage reporting:
```bash
cd frontend
npx vitest run --coverage
```
*Frontend test coverage is maintained at **100%** line coverage across components, hooks, and API services.*

---

## 🐳 Docker Deployment

The application is fully containerized and can be launched locally using Docker Compose:

1. Build and start the entire multi-container service stack (Postgres Database, FastAPI Backend, and Nginx Frontend proxying):
   ```bash
   docker-compose up --build -d
   ```
2. The services will be active at:
   * **Frontend Dashboard:** `http://localhost`
   * **FastAPI Backend Swagger docs:** `http://localhost:8000/docs`
