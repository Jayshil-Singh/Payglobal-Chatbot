import smtplib
from email.message import EmailMessage


def send_email(*, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str, to_email: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as smtp:
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)
