# PayGlobal AI Assistant

Enterprise-oriented internal chatbot for PayGlobal implementation support using Streamlit + RAG.

## Quick Start

1. Copy `.env.example` to `.env`.
2. Set `GROK_API_KEY`.
3. (First run only) set `ADMIN_BOOTSTRAP_PASSWORD` to create the admin account.
4. Run:
   - `setup.bat`
   - `run.bat`

After first successful admin login, clear `ADMIN_BOOTSTRAP_PASSWORD` in `.env`.

## Admin Account Recovery (Locked Out)

If you cannot sign in and need to reset/create the admin user locally:

- Run `reset_admin.bat`, set a new password, then sign in with username `admin`.

Advanced / non-interactive:

```bash
py -3 scripts/reset_admin_password.py --username admin --password "NewStrongPassword123"
```

## Security Defaults

- URL-based session tokens have been removed.
- Default hardcoded admin password has been removed.
- Feedback writes enforce a single vote per user per answer.
- Runtime artifacts are git-ignored (`data/logs`, ingest manifest).
- Failed login lockout is enabled (`MAX_FAILED_LOGIN_ATTEMPTS`, `LOGIN_LOCKOUT_MINUTES`).
- Admin can disable/enable accounts and unlock locked users.

## Production Guidance

- Keep `ALLOW_DANGEROUS_DESERIALIZATION=false`.
- Use a managed secrets store for `.env` values.
- For multi-user scale, set `DATABASE_URL` to Postgres and run migrations:
  - `py -3 scripts/db_migrate.py`
- Add CI checks (lint/tests/security scans) before deployment.

## Enterprise SSO (Trusted Header)

For enterprise SSO behind a reverse proxy:

- Set `SSO_HEADER_USERNAME` (for example `X-Auth-Request-Email`)
- Optionally set `SSO_ADMIN_USERS` (comma separated)
- Optionally keep `SSO_AUTO_PROVISION=true`

Your proxy must authenticate users and inject the trusted header.

## Quality Gates

- CI workflow: `.github/workflows/ci.yml`
- Automated tests: `tests/`
- Local test run:
  - `py -3 -m pip install pytest python-dotenv bcrypt`
  - `py -3 -m pytest -q -p no:cacheprovider`

## Operations and Security Docs

- Security policy: `SECURITY.md`
- Ops runbook: `RUNBOOK.md`
