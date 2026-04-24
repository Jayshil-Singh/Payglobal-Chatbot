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

## Security Defaults

- URL-based session tokens have been removed.
- Default hardcoded admin password has been removed.
- Feedback writes enforce a single vote per user per answer.
- Runtime artifacts are git-ignored (`data/logs`, ingest manifest).

## Production Guidance

- Keep `ALLOW_DANGEROUS_DESERIALIZATION=false`.
- Use a managed secrets store for `.env` values.
- Move from SQLite to Postgres for multi-user scale.
- Add CI checks (lint/tests/security scans) before deployment.

## Quality Gates

- CI workflow: `.github/workflows/ci.yml`
- Automated tests: `tests/`
- Local test run:
  - `py -3 -m pip install pytest python-dotenv bcrypt`
  - `py -3 -m pytest -q -p no:cacheprovider`

## Suggested Next Refactor

- Split `app.py` into:
  - `ui/auth_view.py`
  - `ui/chat_view.py`
  - `ui/admin_view.py`
  - `services/chat_service.py`
  - `services/security.py`
