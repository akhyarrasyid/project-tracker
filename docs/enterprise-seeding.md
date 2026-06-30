# Enterprise Seeding

Seed system sekarang sudah berubah dari flat task importer menjadi profile-based enterprise data generator.

## Profiles

- `smoke`
  - kecil, cepat, cocok untuk local validation dan CI
- `demo`
  - lebih padat untuk browser walkthrough dan screenshot
- `enterprise_demo`
  - dataset besar dengan project, membership, issue, comment, watcher, notification, activity, dan attachment metadata yang terasa seperti workspace enterprise sungguhan

## Data Model Coverage

Seed generator mengisi:

- departments
- teams
- users
- projects
- project_members
- sprints
- epics
- labels
- tasks
- task_labels
- comments
- watchers
- attachments
- notifications
- activity_logs

Selain itu generator juga:

- menjaga issue number per project;
- membangun parent-child issue links;
- membangun dependencies;
- menghitung `comments_count`, `attachments_count`, dan `watchers_count`;
- mengisi blocked issue dengan `is_blocked` dan `blocked_reason`;
- menjaga rerun tetap idempotent lewat natural key seeding.

## Seed Sources

Struktur seed ada di:

```text
backend/app/db/seeds/
  catalogs/
  profiles/
  scenarios/
```

- `catalogs/`
  - organisasi, orang, labels, project templates, issue templates
- `profiles/`
  - target count dan scope project
- `scenarios/`
  - anchor story realistis lintas domain seperti payments, privacy, support, finance, dan people ops

## Local Commands

Jalankan PostgreSQL test lokal terisolasi:

```powershell
.\backend\scripts\start_test_postgres.ps1
```

Validasi profile:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.services.seed_service --validate --profile smoke
```

Dry run dengan report:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.services.seed_service --dry-run --profile enterprise_demo --report .runtime\enterprise-seed-report.json
```

Seed ke local database:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.services.seed_service --seed --profile demo
```

Reset seeded projects untuk profile tertentu:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.services.seed_service --reset-profile --profile demo
```

## Remote Safety

Remote seed tidak akan berjalan kecuali dua environment variable ini diberikan eksplisit:

```text
ALLOW_REMOTE_SEED=1
SEED_CONFIRM_PROFILE=<profile-name>
```

Contoh:

```powershell
$env:ALLOW_REMOTE_SEED="1"
$env:SEED_CONFIRM_PROFILE="enterprise_demo"
```

Tanpa dua flag ini, seed service akan berhenti sebelum menulis ke host non-local.

## Notes

- Runtime application tetap membaca `DATABASE_URL`.
- `SUPABASE_DATABASE_URL` tetap khusus untuk verification eksplisit, bukan runtime.
- Seed service tidak menjalankan migration atau `create_all()`.
- Seed service mengasumsikan schema sudah dikelola Alembic.
