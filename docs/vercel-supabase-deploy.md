# Vercel + Supabase Deploy Checklist

This repository stays as one GitHub monorepo:

```text
project-tracker/
|-- frontend/
`-- backend/
```

Deploy it to Vercel as two separate projects.

## 1. Generate a Production Secret

Create a production `SECRET_KEY` locally:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Example output:

```text
Cm3wu09bDP7yIzB_gn9IY1EUZrPlTKsb-WusHuBkSRMoCoH4Q6wf5dHWA7_bowxJ1ksXQnnLeGBo6BdUWWHQLA
```

Use your own generated value and never commit it.

## 2. Deploy the Backend Project

1. Create a new Vercel project from this repository.
2. Set **Root Directory** to `backend`.
3. Add these environment variables:

```text
DATABASE_URL=postgresql://postgres.your-project:password@aws-1-region.pooler.supabase.com:5432/postgres
SECRET_KEY=<paste-generated-secret>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=["https://technical-test-project-tracker.vercel.app"]
```

4. Deploy the backend.
5. Copy the deployed backend URL, for example:

```text
https://technical-test-project-tracker-api.vercel.app
```

## 3. Deploy the Frontend Project

1. Create a second Vercel project from the same repository.
2. Set **Root Directory** to `frontend`.
3. Add this environment variable:

```text
VITE_API_URL=https://technical-test-project-tracker-api.vercel.app
```

4. Deploy the frontend.

## 4. Finalize Backend CORS

If the frontend domain differs from the expected URL, update the backend `CORS_ORIGINS` value to the real frontend domain exactly:

```text
["https://technical-test-project-tracker.vercel.app"]
```

Redeploy the backend after saving the change.

## 5. Local Development Example

```text
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/project_tracker
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/project_tracker_test
TEST_DATABASE_ADMIN_URL=postgresql://postgres:postgres@localhost:5432/postgres
SUPABASE_DATABASE_URL=postgresql://postgres.your-project:password@aws-1-region.pooler.supabase.com:5432/postgres

SECRET_KEY=replace-me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

CORS_ORIGINS=["http://localhost:5173","https://technical-test-project-tracker.vercel.app"]
VITE_API_URL=http://localhost:8000
```

## 6. Post-Deploy Smoke Check

1. Open the frontend URL.
2. Log in successfully.
3. Open a project board.
4. Open an issue detail route directly.
5. Confirm API calls go to the deployed backend origin.
6. Confirm there are no CORS errors in the browser console.
