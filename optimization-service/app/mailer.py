"""
Servicio de envío de emails — optimization-service.
Usa smtplib estándar con TLS (Gmail App Password).
Nunca lanza excepción al caller — loguea el error y retorna False.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, NOTIFY_EMAIL

log = logging.getLogger("optimization")


def send_rejection_notification(
    proposal_id: str,
    product_id: str,
    product_name: str,
    ean_code: str,
    size_name: str,
    manufacturer_name: str,
    rejection_reason: str,
) -> bool:
    """
    Envía una notificación a Oficina Técnica cuando un fabricante rechaza una propuesta.
    Retorna True si el envío fue exitoso, False si falló (o si SMTP no está configurado).
    """
    if not SMTP_USER or not SMTP_PASSWORD or not NOTIFY_EMAIL:
        log.warning("SMTP not configured — skipping rejection notification email")
        return False

    subject = f"[Packaging Optimizer] Propuesta rechazada — {product_name} · EAN {ean_code}"

    html_body = f"""
    <html>
      <body style="font-family: 'Helvetica Neue', Arial, sans-serif; color: #111; background: #fff; padding: 40px;">
        <h2 style="font-weight: 300; font-size: 24px; margin-bottom: 8px;">Propuesta de embalaje rechazada</h2>
        <p style="font-size: 14px; color: #555; margin-bottom: 24px;">
          Se ha registrado un rechazo de propuesta que requiere intervención del equipo de Oficina Técnica.
        </p>

        <table style="border-collapse: collapse; width: 100%; font-size: 13px; margin-bottom: 32px;">
          <tr style="border-bottom: 1px solid #e8e8e8;">
            <td style="padding: 10px 0; color: #888; width: 180px; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em;">Producto</td>
            <td style="padding: 10px 0; font-weight: 600;">{product_name}</td>
          </tr>
          <tr style="border-bottom: 1px solid #e8e8e8;">
            <td style="padding: 10px 0; color: #888; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em;">EAN</td>
            <td style="padding: 10px 0; font-family: monospace;">{ean_code or "—"}</td>
          </tr>
          <tr style="border-bottom: 1px solid #e8e8e8;">
            <td style="padding: 10px 0; color: #888; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em;">Talla</td>
            <td style="padding: 10px 0;">{size_name}</td>
          </tr>
          <tr style="border-bottom: 1px solid #e8e8e8;">
            <td style="padding: 10px 0; color: #888; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em;">Proveedor</td>
            <td style="padding: 10px 0;">{manufacturer_name}</td>
          </tr>
          <tr>
            <td style="padding: 10px 0; color: #888; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em;">Motivo</td>
            <td style="padding: 10px 0; color: #c00;">{rejection_reason or "No especificado"}</td>
          </tr>
        </table>

        <p style="font-size: 13px; color: #555;">
          Es necesario revisar manualmente esta configuración de embalaje y contactar con el proveedor para determinar una solución alternativa.
        </p>

        <hr style="border: none; border-top: 1px solid #e8e8e8; margin: 32px 0;" />
        <p style="font-size: 11px; color: #aaa;">Packaging Optimizer · Sistema de optimización de embalaje · TFG UOC 2026</p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_FROM
    msg["To"]      = NOTIFY_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, NOTIFY_EMAIL, msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, NOTIFY_EMAIL, msg.as_string())
        log.info("Rejection notification sent for proposal %s", proposal_id)
        return True
    except Exception as exc:
        log.error("Failed to send rejection notification for proposal %s: %s", proposal_id, exc)
        return False
