import smtplib
from email.message import EmailMessage

import requests

from config import APP_LINK


def send_email(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    to_email: str,
    subject: str,
    body: str,
    sendgrid_api_key: str = "",
    sendgrid_from_email: str = "",
) -> None:
    smtp_user = (smtp_user or "").strip()
    # Gmail app passwords are often copied with spaces for readability.
    smtp_password = "".join((smtp_password or "").split())
    sendgrid_api_key = (sendgrid_api_key or "").strip()
    sendgrid_from_email = (sendgrid_from_email or "").strip()

    if sendgrid_api_key:
        from_email = sendgrid_from_email or smtp_user
        if not from_email:
            raise RuntimeError("SENDGRID_FROM_EMAIL (or SMTP_USER) is required when SENDGRID_API_KEY is set.")
        resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {sendgrid_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": from_email},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
            },
            timeout=30,
        )
        if resp.status_code >= 300:
            raise RuntimeError(f"SendGrid delivery failed: {resp.status_code} {resp.text[:300]}")
        return

    # Ensure every email includes a direct login link for operator convenience.
    if APP_LINK and APP_LINK.strip() and APP_LINK not in body:
        body = (body or "").rstrip() + f"\n\nLog in here: {APP_LINK}\n"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(body)

    last_err = None

    # 1) Try SSL first (typical for port 465)
    try:
        with smtplib.SMTP_SSL(smtp_host, int(smtp_port), timeout=30) as smtp:
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)
            return
    except Exception as exc:
        last_err = exc

    # 2) Fallback to STARTTLS on 587 (common cloud-safe route)
    try:
        with smtplib.SMTP(smtp_host, 587, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)
            return
    except Exception as exc:
        last_err = exc

    raise RuntimeError(f"SMTP delivery failed: {last_err}")
