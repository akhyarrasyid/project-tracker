# GitHub Actions + Vercel

This repository now includes four GitHub Actions workflows:

- `build.yml`
  - Runs backend tests and lint against isolated local PostgreSQL in CI.
  - Runs frontend tests, lint, and production build.
- `deploy.yml`
  - Deploys backend and frontend to two separate Vercel projects.
  - Push to `main` deploys production automatically.
  - Manual dispatch can deploy `production` or `preview`.
- `rollback.yml`
  - Manually rolls back a frontend deployment, backend deployment, or both.
- `cleanup.yml`
  - Manually removes preview deployments by URL or deployment ID.

## Required GitHub Secrets

Add these repository secrets before using the Vercel workflows:

```text
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_FRONTEND_PROJECT_ID
VERCEL_BACKEND_PROJECT_ID
```

## Vercel Project Layout

Use two separate Vercel projects from the same GitHub repository:

```text
technical-test-project-tracker
  root directory: frontend

technical-test-project-tracker-api
  root directory: backend
```

The workflow assumes environment variables are already configured in each Vercel project:

- Backend project:
  - `DATABASE_URL`
  - `SECRET_KEY`
  - `ALGORITHM`
  - `ACCESS_TOKEN_EXPIRE_MINUTES`
  - `REFRESH_TOKEN_EXPIRE_DAYS`
  - `CORS_ORIGINS`
- Frontend project:
  - `VITE_API_URL`

## Manual Workflow Examples

### Deploy preview

Run `Deploy` from the GitHub Actions UI with:

```text
target_environment=preview
git_ref=feature/my-branch
```

### Roll back production

Run `Rollback` from the GitHub Actions UI with one or both inputs:

```text
frontend_target=https://technical-test-project-tracker-previous.vercel.app
backend_target=https://technical-test-project-tracker-api-previous.vercel.app
```

### Remove preview deployments

Run `Cleanup` from the GitHub Actions UI with one or both inputs:

```text
frontend_preview_target=https://technical-test-project-tracker-git-feature-preview.vercel.app
backend_preview_target=https://technical-test-project-tracker-api-git-feature-preview.vercel.app
```

## Notes

- `deploy.yml` does not sync environment variables from GitHub to Vercel. Keep them managed in the Vercel dashboard.
- `cleanup.yml` uses `vercel remove --safe` so it refuses to remove active production deployments.
- `rollback.yml` is intentionally manual because rollback targets should be chosen explicitly.
