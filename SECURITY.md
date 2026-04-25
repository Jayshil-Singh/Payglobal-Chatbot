# Security Policy

## Supported Deployment Model

This project is intended for internal enterprise use with controlled access.
The production baseline includes:

- Secrets managed outside source control.
- `ALLOW_DANGEROUS_DESERIALIZATION=false`.
- Admin-managed user onboarding (no self-registration).
- Password hashing via `bcrypt`.
- Account lockout on repeated failed logins.

## Reporting a Vulnerability

Do not open public issues for security vulnerabilities.

- Contact the repository owner privately.
- Include reproduction steps, impacted files, and severity.
- If possible, include a minimal patch or mitigation suggestion.

## Secrets and Credentials

- Never commit `.env` or real API keys/passwords.
- Rotate any credential immediately if exposed.
- Prefer HTTPS-based email delivery (SendGrid API) in cloud environments.
- Keep `ADMIN_BOOTSTRAP_PASSWORD` empty after first admin bootstrap.

## Authentication and Access Control

- Passwords are stored as salted `bcrypt` hashes.
- User accounts can be disabled by admins.
- Failed login attempts trigger temporary account lockout.
- New users receive temporary credentials and are forced to change password.

## Hardening Checklist

- Keep dependencies updated (`pip-audit` in CI).
- Run `ruff`, `bandit`, and tests before deploy.
- Restrict admin role assignment to trusted operators.
- Backup database on a schedule and test restores.
