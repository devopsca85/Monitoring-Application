import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.models import Alert, AlertStatus, MonitoringResult, Site
from app.services.notification_service import send_alert

logger = logging.getLogger(__name__)

CONSECUTIVE_FAILURES_THRESHOLD = 3


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

    # Check consecutive failures
    recent_results = (
        db.query(MonitoringResult)
        .filter(MonitoringResult.site_id == site.id)
        .order_by(MonitoringResult.checked_at.desc())
        .limit(CONSECUTIVE_FAILURES_THRESHOLD)
        .all()
    )

    consecutive_failures = sum(
        1 for r in recent_results if r.status != AlertStatus.OK
    )

    if consecutive_failures >= CONSECUTIVE_FAILURES_THRESHOLD:
        existing_alert = (
            db.query(Alert)
            .filter(Alert.site_id == site.id, Alert.resolved == False)
            .first()
        )

        if not existing_alert:
            alert = Alert(
                site_id=site.id,
                alert_type=result.status,
                message=result.error_message or f"Site {site.name} is {result.status.value}",
            )
            db.add(alert)
            db.commit()

            await send_alert(
                channel=site.notification_channel.value,
                to_emails=[
                    e.strip()
                    for e in (site.notification_emails or "").split(",")
                    if e.strip()
                ],
                site_name=site.name,
                status=result.status.value,
                message=result.error_message or f"Site {site.name} has been down for {CONSECUTIVE_FAILURES_THRESHOLD} consecutive checks.",
            )
