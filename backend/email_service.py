"""SMTP email sender for CookPilot (admin-configured via DB)."""
import logging
import aiosmtplib
from email.message import EmailMessage
from db import get_settings

logger = logging.getLogger(__name__)


async def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    settings = await get_settings()
    host = settings.get("smtp_host") or ""
    if not host:
        logger.warning("SMTP nicht konfiguriert - E-Mail an %s wird nicht gesendet", to_email)
        return False

    msg = EmailMessage()
    msg["From"] = settings.get("smtp_from") or settings.get("smtp_user") or "noreply@cookpilot.local"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text_body or "HTML E-Mail - bitte HTML-fähiger Client benutzen.")
    msg.add_alternative(html_body, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=host,
            port=int(settings.get("smtp_port") or 587),
            username=settings.get("smtp_user") or None,
            password=settings.get("smtp_password") or None,
            start_tls=bool(settings.get("smtp_use_tls", True)),
            timeout=15,
        )
        return True
    except Exception as exc:
        logger.error("SMTP Versand fehlgeschlagen: %s", exc)
        return False


def build_invite_email(app_name: str, invite_url: str, inviter_name: str) -> tuple[str, str]:
    html = f"""
    <div style="font-family: Manrope, Arial, sans-serif; background:#FAF8F5; padding:40px; color:#1C1C1C;">
      <div style="max-width:560px; margin:0 auto; background:#ffffff; border:1px solid #E5DFD3; border-radius:24px; padding:40px;">
        <h1 style="font-size:28px; margin:0 0 12px; color:#C8553D;">Willkommen bei {app_name}</h1>
        <p style="font-size:16px; line-height:1.6;">
          {inviter_name} hat dich zu <strong>{app_name}</strong> eingeladen - deinem intelligenten Küchen-Assistenten.
        </p>
        <p style="margin:32px 0;">
          <a href="{invite_url}" style="display:inline-block; background:#C8553D; color:#ffffff; padding:16px 28px; border-radius:16px; text-decoration:none; font-weight:700;">
            Konto erstellen
          </a>
        </p>
        <p style="color:#6B655C; font-size:14px;">
          Falls der Button nicht funktioniert: {invite_url}
        </p>
      </div>
    </div>
    """
    text = f"Hallo,\n\n{inviter_name} hat dich zu {app_name} eingeladen.\n\nKonto erstellen: {invite_url}\n"
    return html, text
