import json
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_email_alert(to_emails: list[str], subject: str, body: str) -> bool:
    if not settings.AZURE_COMM_CONNECTION_STRING:
        logger.warning("Azure Communication Services not configured, skipping email")
        return False

    try:
        from azure.communication.email import EmailClient

        client = EmailClient.from_connection_string(
            settings.AZURE_COMM_CONNECTION_STRING
        )
        message = {
            "senderAddress": settings.AZURE_COMM_SENDER_EMAIL,
            "recipients": {
                "to": [{"address": email} for email in to_emails],
            },
            "content": {
                "subject": subject,
                "html": body,
            },
        }
        poller = client.begin_send(message)
        poller.result()
        logger.info(f"Email sent to {to_emails}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


async def send_teams_alert(title: str, message: str, color: str = "FF0000") -> bool:
    if not settings.TEAMS_WEBHOOK_URL:
        logger.warning("Teams webhook not configured, skipping notification")
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
                settings.TEAMS_WEBHOOK_URL,
                json=card,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            logger.info("Teams notification sent")
            return True
    except Exception as e:
        logger.error(f"Failed to send Teams notification: {e}")
        return False


async def send_alert(
    channel: str,
    to_emails: list[str],
    site_name: str,
    status: str,
    message: str,
) -> None:
    subject = f"[{status.upper()}] Monitoring Alert: {site_name}"
    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px;">
        <div style="background: {'#b82105' if status == 'critical' else '#fc5c1d'}; color: white; padding: 16px 24px; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0;">{subject}</h2>
        </div>
        <div style="background: #f8f9fa; padding: 24px; border-radius: 0 0 8px 8px; border: 1px solid #e9ecef;">
            <p><strong>Site:</strong> {site_name}</p>
            <p><strong>Status:</strong> {status}</p>
            <p><strong>Details:</strong> {message}</p>
        </div>
    </div>
    """

    color_map = {"critical": "FF0000", "warning": "FFA500", "ok": "00FF00"}
    teams_color = color_map.get(status, "FF0000")

    if channel in ("email", "both") and to_emails:
        await send_email_alert(to_emails, subject, html_body)

    if channel in ("teams", "both"):
        await send_teams_alert(subject, message, teams_color)
