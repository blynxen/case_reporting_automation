
import smtplib
from email.message import EmailMessage
from typing import List
import os


def _bool_env(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def send_email(subject: str, body: str, to: List[str] | None, attachment_path: str):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    sender = os.getenv("EMAIL_FROM")

    # Permitir EMAIL_TO no .env como lista separada por vírgula
    if not to:
        to_env = os.getenv("EMAIL_TO", "")
        to = [x.strip() for x in to_env.split(",") if x.strip()]

    if not to:
        raise ValueError("Nenhum destinatário definido (EMAIL_TO vazio)")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    msg.set_content(body)

    with open(attachment_path, "rb") as f:
        file_data = f.read()
        file_name = os.path.basename(attachment_path)
    msg.add_attachment(file_data, maintype="application", subtype="xml", filename=file_name)

    use_ssl = _bool_env("SMTP_USE_SSL", "false")
    use_starttls = _bool_env("SMTP_STARTTLS", "true")

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port)
        else:
            server = smtplib.SMTP(host, port)
            if use_starttls:
                server.starttls()

        if user and password:
            server.login(user, password)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass
