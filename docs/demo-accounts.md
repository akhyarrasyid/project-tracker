# Demo Accounts

The `release_demo` seed creates these usernames for product walkthroughs:

- `admin`
- `payment_owner`
- `engineering_member`
- `legal_member`
- `viewer_user`

The shared demo password is not stored in Git.

For local or remote seeding, provide it through:

```text
DEMO_SEED_PASSWORD
```

Remote seeding requires `DEMO_SEED_PASSWORD` to be set before `release_demo` can be written.

Example shell setup:

```powershell
$env:DEMO_SEED_PASSWORD = "set-this-outside-git"
```

The seed service hashes the password through the existing auth flow before storing it.
