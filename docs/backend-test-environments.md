# Backend Test Environments

Backend tests default to an isolated local PostgreSQL database. They do not use SQLite, and they do not use Supabase unless you opt in explicitly for migration or release verification.

## Environment Variables

- `DATABASE_URL`
  - Main backend application database for local development.
- `TEST_DATABASE_URL`
  - Local PostgreSQL database used by `pytest`.
  - Default if unset: `postgresql://postgres:postgres@127.0.0.1:5432/project_tracker_test`
- `TEST_DATABASE_ADMIN_URL`
  - Admin connection used to create `TEST_DATABASE_URL` if it does not exist.
  - Default if unset: same host/credentials as `TEST_DATABASE_URL`, database `postgres`.
- `SUPABASE_DATABASE_URL`
  - Remote Supabase PostgreSQL connection used only for Alembic verification, smoke tests, and final pre-release validation.
- `ALLOW_REMOTE_TEST_DATABASE`
  - Must be set to `1` before backend tests are allowed to run against a remote PostgreSQL host.

## Local PostgreSQL Test Flow

1. Start the local database:

```powershell
docker compose up -d db
```

2. Run backend tests locally:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
```

3. Run backend lint locally:

```powershell
backend\.venv\Scripts\ruff.exe check backend
```

The harness automatically:

- creates `project_tracker_test` if it does not exist;
- creates a unique schema per test session;
- sets `DATABASE_SCHEMA` to that schema;
- rolls back per-test transactions;
- drops the temporary schema after the run.

This keeps test data isolated from `project_tracker`, development data, and any remote database.

## Explicit Supabase Verification

Use Supabase only for migration verification, smoke tests, and final pre-release validation.

```powershell
$env:TEST_DATABASE_URL = $env:SUPABASE_DATABASE_URL
$env:ALLOW_REMOTE_TEST_DATABASE = "1"
backend\.venv\Scripts\python.exe -m pytest backend\tests\integration\test_blocked_flag_migration.py -q
```

After the command finishes:

```powershell
Remove-Item Env:TEST_DATABASE_URL
Remove-Item Env:ALLOW_REMOTE_TEST_DATABASE
```

## Safety Rules

- Do not point `TEST_DATABASE_URL` at `project_tracker`, development, staging, or production databases.
- Remote hosts are rejected by default.
- Non-test database names are rejected by default.
- Supabase verification requires explicit opt-in through `ALLOW_REMOTE_TEST_DATABASE=1`.
