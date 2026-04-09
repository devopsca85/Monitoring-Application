import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.models import Alert, AlertStatus, MonitoringResult, Site
from app.services.notification_service import send_alert

logger = logging.getLogger(__name__)

CONSECUTIVE_FAILURES_THRESHOLD = 3

# HTTP status codes that trigger an immediate alert (no waiting for consecutive failures)
IMMEDIATE_ALERT_CODES = {404, 500, 501, 502, 503, 504}


def _is_immediate_alert(result: MonitoringResult) -> bool:
    """Check if this result should trigger an immediate alert (404, 5XX)."""
    if result.status_code and result.status_code in IMMEDIATE_ALERT_CODES:
        return True
    return False


async def _create_and_send_alert(
    db: Session, site: Site, result: MonitoringResult, message: str
) -> None:
    """Create an alert record and send notification."""
    existing_alert = (
        db.query(Alert)
        .filter(Alert.site_id == site.id, Alert.resolved == False)
        .first()
    )

    if existing_alert:
        return  # Already alerting for this site

    alert = Alert(
        site_id=site.id,
        alert_type=result.status,
        message=message,
    )
    db.add(alert)
    db.commit()

    to_emails = [
        e.strip()
        for e in (site.notification_emails or "").split(",")
        if e.strip()
    ]

    await send_alert(
        channel=site.notification_channel.value,
        to_emails=to_emails,
        site_name=site.name,
        status=result.status.value,
        message=message,
    )


async def evaluate_and_alert(db: Session, result: MonitoringResult) -> None:
    site = db.query(Site).filter(Site.id == result.site_id).first()
    if not site:
        return

    if result.status == AlertStatus.OK:
        # Resolve any open alerts
        open_alerts = (
            db.query(Alert)
            .filter(Alert.site_id == site.id, Alert.resolved == False)
            .all()
        )
        for alert in open_alerts:
            alert.resolved = True
            alert.resolved_at = datetime.now(timezone.utc)

        if open_alerts:
            await send_alert(
                channel=site.notification_channel.value,
                to_emails=(site.notification_emails or "").split(","),
                site_name=site.name,
                status="ok",
                message=f"{site.name} ({site.url}) is back online.",
            )
        db.commit()
        return

    # INSTANT ALERT on any failure — no waiting for consecutive failures
    if _is_immediate_alert(result):
        error_msg = (
            f"HTTP {result.status_code} error on {site.name} ({site.url}). "
            f"{result.error_message or ''}"
        ).strip()
    else:
        error_msg = (
            result.error_message
            or f"Site {site.name} ({site.url}) is {result.status.value}."
        )

    logger.warning(f"Instant alert for {site.name}: {result.status.value} — {error_msg}")
    await _create_and_send_alert(db, site, result, error_msg)
