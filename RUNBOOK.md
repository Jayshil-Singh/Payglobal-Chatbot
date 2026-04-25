# Operational Runbook

## 1) Startup

- Set secrets in environment (or Streamlit Cloud secrets):
  - `GROK_API_KEY`
  - `ADMIN_BOOTSTRAP_USER`
  - `ADMIN_BOOTSTRAP_PASSWORD` (first run only)
  - `SMTP_*` or `SENDGRID_*`
- Run:
  - `setup.bat`
  - `run.bat`

After first successful admin login, clear `ADMIN_BOOTSTRAP_PASSWORD`.

## 2) User Provisioning

- Admin creates user from Admin panel.
- App generates temporary password.
- Temporary credentials are sent via email.
- User must change password on first login.

If email fails, share temporary credentials out-of-band and rotate promptly.

## 3) Common Incidents

### Login failures / lockout

- Symptom: user cannot log in after repeated failures.
- Action: admin opens User Management and clicks `Unlock`.
- If needed, reset password and resend temporary password.

### Disabled account

- Symptom: valid credentials but login denied.
- Action: admin clicks `Enable` in User Management.

### Admin account recovery

- Run `reset_admin.bat` locally on server host.
- Or non-interactive:
  - `py -3 scripts/reset_admin_password.py --username admin --password "NewStrongPassword123"`

### Email delivery outage

- Prefer `SENDGRID_API_KEY` + `SENDGRID_FROM_EMAIL`.
- Verify sender authentication (SPF/DKIM).
- Temporarily use secure manual credential handoff with immediate password rotation.

## 4) Verification After Changes

- `py -3 -m py_compile app.py auth.py db.py`
- `py -3 -m pytest -q -p no:cacheprovider`
- `py -3 -m ruff check .`
- `py -3 -m bandit -c bandit.yaml -q -r .`

## 5) Backup and Restore

- Backup `data/payglobal.db` at least daily.
- Keep 7-30 rolling backups based on policy.
- Run quarterly restore drill into a staging environment.

## 6) Security Maintenance

- Review audit log tab weekly.
- Rotate API keys and mail credentials on schedule.
- Re-run dependency scans (`pip-audit`) regularly.
