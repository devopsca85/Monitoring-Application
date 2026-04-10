import logging
import smtplib
from email.mime.text import MIMEText

import httpx

from app.core.database import SessionLocal
from app.core.security import decrypt_credential
from app.models.models import SystemSetting

logger = logging.getLogger(__name__)


def _get_setting(db, key: str) -> str:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not row:
        return ""
    if row.is_encrypted and row.value:
        try:
            return decrypt_credential(row.value)
        except Exception:
            return ""
    return row.value


async def send_email_alert(to_emails: list[str], subject: str, body: str) -> bool:
    """Send email using SMTP settings stored in the database."""
    db = SessionLocal()
    try:
        host = _get_setting(db, "smtp_host")
        if not host:
            logger.warning("SMTP not configured in admin settings, skipping email")
            return False

        port = int(_get_setting(db, "smtp_port") or "587")
        user = _get_setting(db, "smtp_user")
        password = _get_setting(db, "smtp_password")
        from_email = _get_setting(db, "smtp_from_email") or user
        use_tls = _get_setting(db, "smtp_use_tls") != "false"
    finally:
        db.close()

    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)

    try:
        if use_tls:
            server = smtplib.SMTP(host, port, timeout=15)
            server.starttls()
        else:
            server = smtplib.SMTP(host, port, timeout=15)
        if user and password:
            server.login(user, password)
        server.sendmail(from_email, to_emails, msg.as_string())
        server.quit()
        logger.info(f"Email sent to {to_emails}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email via SMTP: {e}")
        return False


async def send_teams_alert(title: str, message: str, color: str = "FF0000") -> bool:
    """Send Teams notification using webhook URL stored in the database."""
    db = SessionLocal()
    try:
        webhook_url = _get_setting(db, "teams_webhook_url")
    finally:
        db.close()

    if not webhook_url:
        logger.warning("Teams webhook not configured in admin settings, skipping")
        return False

    try:
        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color,
            "summary": title,
            "sections": [
                {
                    "activityTitle": title,
                    "text": message,
                    "markdown": True,
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                webhook_url,
                json=card,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            logger.info("Teams notification sent")
            return True
    except Exception as e:
        logger.error(f"Failed to send Teams notification: {e}")
        return False


async def send_admin_notification(subject: str, message: str) -> None:
    """Send a notification to all admin users (email + Teams if configured)."""
    from app.models.models import User

    db = SessionLocal()
    try:
        admins = db.query(User).filter(User.is_admin == True, User.is_active == True).all()
        admin_emails = [a.email for a in admins if a.email]
        teams_configured = bool(_get_setting(db, "teams_webhook_url"))
    finally:
        db.close()

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px;">
        <div style="background: #fc5c1d; color: white; padding: 16px 24px; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0;">{subject}</h2>
        </div>
        <div style="background: #f8f9fa; padding: 24px; border-radius: 0 0 8px 8px; border: 1px solid #e9ecef;">
            <p>{message}</p>
        </div>
    </div>
    """

    if admin_emails:
        await send_email_alert(admin_emails, subject, html_body)

    if teams_configured:
        await send_teams_alert(subject, message, "FFA500")


async def send_alert(
    channel: str,
    to_emails: list[str],
    site_name: str,
    status: str,
    message: str,
) -> None:
    subject = f"[{status.upper()}] Monitoring Alert: {site_name}"

    color_map_email = {
        "ok": "#38a169",
        "warning": "#fc5c1d",
        "critical": "#b82105",
    }
    banner_color = color_map_email.get(status, "#b82105")
    status_emoji = {"ok": "RECOVERED", "warning": "WARNING", "critical": "DOWN"}.get(status, status.upper())

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px;">
        <div style="background: {banner_color}; color: white; padding: 16px 24px; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0;">[{status_emoji}] {site_name}</h2>
        </div>
        <div style="background: #f8f9fa; padding: 24px; border-radius: 0 0 8px 8px; border: 1px solid #e9ecef;">
            <p><strong>Site:</strong> {site_name}</p>
            <p><strong>Status:</strong> <span style="color: {banner_color}; font-weight: bold;">{status.upper()}</span></p>
            <p><strong>Details:</strong> {message}</p>
        </div>
    </div>
    """

    color_map = {"critical": "FF0000", "warning": "FFA500", "ok": "00FF00"}
    teams_color = color_map.get(status, "FF0000")

    # Send email based on site-level channel setting
    if channel in ("email", "both") and to_emails:
        await send_email_alert(to_emails, subject, html_body)

    # Teams: send if webhook is configured AND enabled
    db = SessionLocal()
    try:
        teams_configured = bool(_get_setting(db, "teams_webhook_url"))
        teams_enabled = _get_setting(db, "teams_enabled") != "false"
    finally:
        db.close()

    if teams_configured and teams_enabled:
        await send_teams_alert(subject, message, teams_color)
