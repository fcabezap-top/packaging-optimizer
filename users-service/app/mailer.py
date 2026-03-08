"""
Servicio de envío de emails.
Usa smtplib estándar con TLS (Gmail App Password).
Nunca lanza excepción al caller — loguea el error y retorna False.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, FRONTEND_URL

log = logging.getLogger("users")


def send_reset_email(to_email: str, token: str) -> bool:
    """
    Envía el correo de recuperación de contraseña.
    Retorna True si el envío fue exitoso, False si falló.
    """
    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"

    subject = "Recuperación de contraseña — Packaging Optimizer"

    html_body = f"""
    <html>
      <body style="font-family: 'Helvetica Neue', Arial, sans-serif; color: #111; background: #fff; padding: 40px;">
        <h2 style="font-weight: 300; font-size: 24px; margin-bottom: 8px;">Recuperación de contraseña</h2>
        <p style="font-size: 14px; color: #555; margin-bottom: 32px;">
          Hemos recibido una solicitud para restablecer la contraseña de tu cuenta en <strong>Packaging Optimizer</strong>.
        </p>
        <a href="{reset_link}"
           style="display: inline-block; background: #000; color: #fff; text-decoration: none;
                  padding: 12px 24px; font-size: 12px; font-weight: 600; letter-spacing: 0.1em;
                  text-transform: uppercase;">
          Restablecer contraseña
        </a>
        <p style="font-size: 12px; color: #888; margin-top: 32px;">
          Este enlace es válido durante <strong>1 hora</strong>. Si no solicitaste este cambio, ignora este correo.
        </p>
        <hr style="border: none; border-top: 1px solid #e8e8e8; margin: 32px 0;" />
        <p style="font-size: 11px; color: #aaa;">Packaging Optimizer · TFG</p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_FROM
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        log.info("Reset email sent to %s", to_email)
        return True
    except Exception as exc:
        log.error("Failed to send reset email to %s: %s", to_email, exc)
        return False
