import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.models import Alert, AlertStatus, MonitoringResult, Site
from app.services.notification_service import send_alert

logger = logging.getLogger(__name__)

IMMEDIATE_ALERT_CODES = {404, 500, 501, 502, 503, 504}

# Slowness: only alert if site has been slow for this many minutes
SLOW_SUSTAINED_MINUTES = 15


def _is_immediate_alert(result: MonitoringResult) -> bool:
    if result.status_code and result.status_code in IMMEDIATE_ALERT_CODES:
        return True
    return False


def _is_sustained_slowness(db: Session, site: Site, slow_threshold: int) -> bool:
    """Check if the site has been consistently slow for the past SLOW_SUSTAINED_MINUTES."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=SLOW_SUSTAINED_MINUTES)

    recent = (
        db.query(MonitoringResult)
        .filter(
            MonitoringResult.site_id == site.id,
            MonitoringResult.checked_at >= cutoff,
        )
        .order_by(MonitoringResult.checked_at.desc())
        .all()
    )

    if len(recent) < 2:
        # Not enough data points yet — don't alert
        logger.info(f"Slowness check for {site.name}: only {len(recent)} results in last {SLOW_SUSTAINED_MINUTES}m, skipping")
        return False

    # Check if ALL results in the window are slow
    all_slow = all(
        (r.response_time_ms or 0) > slow_threshold
        for r in recent
    )

    logger.info(
        f"Slowness check for {site.name}: {len(recent)} results in last {SLOW_SUSTAINED_MINUTES}m, "
        f"all slow={all_slow}, threshold={slow_threshold}ms"
    )
    return all_slow


async def _create_and_send_alert(
    db: Session, site: Site, result: MonitoringResult, message: str
) -> None:
    """Create an alert record and send notification."""
    try:
        status_enum = result.status
        status_str = status_enum.value if hasattr(status_enum, 'value') else str(status_enum)

        existing_alert = (
            db.query(Alert)
            .filter(Alert.site_id == site.id, Alert.resolved == False)
            .first()
        )

        if existing_alert:
            existing_alert.message = message
            existing_alert.alert_type = status_enum
            db.commit()
            logger.info(f"Updated existing alert #{existing_alert.id} for {site.name}")
            return

        alert = Alert(
            site_id=site.id,
            alert_type=status_enum,
            message=message,
            notified=True,
            notified_at=datetime.now(timezone.utc),
            resolved=False,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        logger.info(f"ALERT CREATED #{alert.id} for {site.name}: {status_str} — {message[:100]}")

        to_emails = [
            e.strip()
            for e in (site.notification_emails or "").split(",")
            if e.strip()
        ]

        try:
            await send_alert(
                channel=site.notification_channel.value,
                to_emails=to_emails,
                site_name=site.name,
                status=status_str,
                message=message,
            )
            logger.info(f"Alert notification sent for {site.name}")
        except Exception as ne:
            logger.error(f"Notification send failed for {site.name} (alert still created): {ne}")

    except Exception as e:
        logger.error(f"ALERT CREATION FAILED for {site.name}: {e}", exc_info=True)


async def evaluate_and_alert(db: Session, result: MonitoringResult) -> None:
    try:
        site = db.query(Site).filter(Site.id == result.site_id).first()
        if not site:
            logger.warning(f"evaluate_and_alert: site {result.site_id} not found")
            return

        logger.info(
            f"evaluate_and_alert: site={site.name}, status={result.status.value}, "
            f"code={result.status_code}, response={result.response_time_ms}ms, "
            f"error={result.error_message or 'none'}"
        )

        if result.status == AlertStatus.OK:
            slow_threshold = site.slow_threshold_ms or 10000
            response_time = result.response_time_ms or 0

            if response_time > slow_threshold:
                # Site is slow — but only alert if sustained for 15+ minutes
                if _is_sustained_slowness(db, site, slow_threshold):
                    slow_msg = (
                        f"SUSTAINED SLOWNESS: {site.name} ({site.url}) has been responding "
                        f"above {slow_threshold}ms for the past {SLOW_SUSTAINED_MINUTES} minutes. "
                        f"Latest: {int(response_time)}ms"
                    )
                    logger.warning(f"Sustained slowness alert for {site.name}")

                    result.status = AlertStatus.WARNING
                    result.error_message = slow_msg
                    db.commit()

                    await _create_and_send_alert(db, site, result, slow_msg)
                else:
                    logger.info(
                        f"Site {site.name} is slow ({int(response_time)}ms > {slow_threshold}ms) "
                        f"but not sustained yet — no alert"
                    )
                return

            # Site is OK and fast — resolve any open alerts
            open_alerts = (
                db.query(Alert)
                .filter(Alert.site_id == site.id, Alert.resolved == False)
                .all()
            )
            for alert in open_alerts:
                alert.resolved = True
                alert.resolved_at = datetime.now(timezone.utc)
                logger.info(f"Resolved alert #{alert.id} for {site.name}")

            if open_alerts:
                try:
                    await send_alert(
                        channel=site.notification_channel.value,
                        to_emails=(site.notification_emails or "").split(","),
                        site_name=site.name,
                        status="ok",
                        message=f"{site.name} ({site.url}) is back online. Response: {int(response_time)}ms",
                    )
                except Exception as e:
                    logger.error(f"Failed to send recovery alert for {site.name}: {e}")
            db.commit()
            return

        # Any non-OK status triggers an immediate alert
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

        logger.warning(f"Alert for {site.name}: {result.status.value} — {error_msg[:100]}")
        await _create_and_send_alert(db, site, result, error_msg)

    except Exception as e:
        logger.error(f"evaluate_and_alert failed for site_id={result.site_id}: {e}", exc_info=True)
