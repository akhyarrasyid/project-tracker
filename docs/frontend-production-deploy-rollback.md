# Frontend Production Deploy and Rollback Guide

This project uses **native Vercel Git integration** as the production source of truth for the frontend.

Production frontend:

```text
https://technical-test-project-tracker.vercel.app
```

Production backend API:

```text
https://technical-test-project-tracker-api.vercel.app
```

## Current Frontend Deployment Model

- Repository: `akhyarrasyid/project-tracker`
- Production branch: `main`
- Vercel project root: `frontend`
- Framework: `Vite`
- Build command: `npm run build`
- Output directory: `dist`
- API environment variable:

```text
VITE_API_URL=https://technical-test-project-tracker-api.vercel.app
```

## Build Identity

The frontend exposes a non-sensitive build identity in two places:

- login screen footer;
- workspace sidebar footer.

Format:

```text
Build <short_sha> · <version>
```

Use this to verify that production is serving the expected commit.

## Safe Deploy Flow

Use this flow whenever frontend changes must reach production.

### 1. Verify Local Quality Gates

Run from `frontend/`:

```powershell
npm.cmd run lint
npm.cmd test -- --run
npm.cmd run build
```

Expected result:

- lint passes with no warnings on touched files;
- tests pass;
- production build succeeds.

### 2. Commit Only the Intended Frontend Changes

Do not use `git add .`.

Stage only the files for the current frontend change:

```powershell
git add frontend/src/...
git add docs/frontend-production-deploy-rollback.md
git add "frontend/src/assets/logo project tracker.png"
```

### 3. Commit on the Working Branch

Example:

```powershell
git commit -m "feat(frontend): polish workspace shell and board visuals"
```

### 4. Merge to `main`

Because native Vercel Git integration deploys from `main`, production updates only after `main` moves forward.

Recommended:

```powershell
git checkout main
git pull
git merge <feature-branch>
git push
```

If GitHub PR flow is preferred, merge the PR into `main` and wait for the native Vercel production deployment to finish.

### 5. Confirm the New Vercel Production Deployment

In Vercel frontend project:

1. Open `Deployments`.
2. Confirm the latest production deployment source SHA matches `origin/main`.
3. Open the production domain.
4. Confirm the build identity shown in the UI matches the latest main commit.

## Production Smoke Checklist

After each frontend deployment, verify:

### Login

- login page loads;
- new logo appears;
- dark or light theme toggle appears;
- no JavaScript crash.

### Workspace shell

- sidebar uses dark navy shell;
- `Inbox` and `My issues` are visible;
- build identity is shown in sidebar footer.

### Board

- open `/projects/PAY/board`;
- issue keys are `PAY-*`, not `WDD-*`;
- no global pagination `1 / 2`;
- board columns use distinct status accents;
- board cards show stronger priority contrast.

### Inbox

- open `/inbox`;
- unread badge appears when data exists;
- notification rows render with grouping and actions.

### Issue detail

- open an issue from board or inbox;
- side panel opens;
- description, comments, activity, watchers, and properties are visible;
- no layout break in light or dark mode.

## Rollback Options

Use the least risky option for the incident.

### Option A — Fastest: Promote a Previous Vercel Deployment

Use this when:

- the latest frontend deploy is broken;
- the previous production deployment is known-good;
- no code change is needed yet.

Steps:

1. Open the frontend Vercel project.
2. Go to `Deployments`.
3. Find the previous healthy deployment.
4. Open its detail page.
5. Promote or assign it back to `Production`.
6. Re-open the production domain.
7. Verify the build identity changed back to the expected older SHA.

After emergency rollback:

- open a fix branch;
- repair the issue;
- redeploy cleanly through `main`.

### Option B — Source-Control Rollback: Revert the Breaking Commit

Use this when:

- the latest deploy should not stay on `main`;
- the fix is to remove one or more recent commits cleanly.

Steps:

```powershell
git checkout main
git pull
git revert <bad_commit_sha>
git push
```

Then wait for native Vercel Git integration to deploy the revert commit.

Verify:

- production build identity matches the new revert commit;
- smoke checklist is green again.

### Option C — Hotfix Forward

Use this when:

- the problem is small and understood;
- a quick fix is safer than serving an older build.

Steps:

1. Create a fix branch from `main`.
2. Apply minimal correction.
3. Run lint, tests, and build.
4. Merge the fix into `main`.
5. Verify new production SHA and smoke results.

## Incident Triage Notes

If production looks older than localhost:

1. Check the build identity in production.
2. Compare it with `git rev-parse --short origin/main`.
3. Inspect the frontend Vercel deployment source SHA.
4. Confirm the production domain still points to the intended frontend Vercel project.
5. Confirm the Vercel project root is still `frontend`.

If production HTML references an old asset filename:

- production is still serving an older deployment;
- browser cache is not the main problem;
- check Vercel deployment source and production alias immediately.

## Things Not To Do During Rollback

- do not deploy from a dirty working tree;
- do not use the custom GitHub Actions deploy workflow as the production source of truth;
- do not change backend environment variables during a frontend-only incident;
- do not overwrite `vercel.json` casually;
- do not use `git reset --hard` on shared work unless explicitly intended.

## Recommended Ownership Split

- Native Vercel Git integration:
  production deployment path
- GitHub Actions build/test/lint:
  quality gate and CI feedback
- Manual custom deploy workflow:
  keep manual-only until fully repaired and revalidated
