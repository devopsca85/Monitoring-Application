import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.utils import enum_val
from app.models.models import Alert, AlertStatus, FalsePositiveRule, MonitoringResult, Site
from app.services.notification_service import send_alert

logger = logging.getLogger(__name__)

IMMEDIATE_ALERT_CODES = {404, 500, 501, 502, 503, 504}

# Slowness: sustained period before alerting
SLOW_SUSTAINED_MINUTES = 15
# Slowness: minimum hours between repeated slow alerts (per site)
SLOW_COOLDOWN_HOURS = 3


def _is_immediate_alert(result: MonitoringResult) -> bool:
    if result.status_code and result.status_code in IMMEDIATE_ALERT_CODES:
        return True
    return False


def _is_sustained_slowness(db: Session, site_id: int, threshold: int) -> bool:
    """Check if site has been consistently slow for SLOW_SUSTAINED_MINUTES."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=SLOW_SUSTAINED_MINUTES)
    recent = (
        db.query(MonitoringResult)
        .filter(MonitoringResult.site_id == site_id, MonitoringResult.checked_at >= cutoff)
        .order_by(MonitoringResult.checked_at.desc())
        .all()
    )
    if len(recent) < 2:
        return False
    return all((r.response_time_ms or 0) > threshold for r in recent)


def _slow_alert_on_cooldown(db: Session, site_id: int) -> bool:
    """Check if a slow alert was already sent in the last SLOW_COOLDOWN_HOURS."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=SLOW_COOLDOWN_HOURS)
    recent_alert = (
        db.query(Alert)
        .filter(
            Alert.site_id == site_id,
            Alert.alert_type.in_([AlertStatus.WARNING, "warning"]),
            Alert.created_at >= cutoff,
        )
        .first()
    )
    return recent_alert is not None


async def _create_and_send_alert(
    db: Session, site: Site, result: MonitoringResult, message: str
) -> None:
    """Create an alert record and send notification."""
    try:
        status_enum = result.status
        status_str = status_enum.value if hasattr(status_enum, 'value') else str(status_enum)

        # FIX #4: Use FOR UPDATE lock to prevent race condition duplicates
        existing_alert = (
            db.query(Alert)
            .with_for_update()
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
        try:
            db.commit()
        except Exception as dup_err:
            db.rollback()
            logger.warning(f"Alert creation conflict for {site.name}, likely duplicate: {dup_err}")
            return
        db.refresh(alert)
        logger.info(f"ALERT CREATED #{alert.id} for {site.name}: {status_str} — {message[:100]}")

        # Check false positive suppression rules before sending notification
        suppressed = False
        fp_rules = (
            db.query(FalsePositiveRule)
            .filter(FalsePositiveRule.site_id == site.id, FalsePositiveRule.is_active == True)
            .all()
        )
        for rule in fp_rules:
            if rule.error_pattern and rule.error_pattern.lower() in message.lower():
                logger.info(f"Alert #{alert.id} suppressed by false positive rule #{rule.id}: '{rule.error_pattern[:60]}'")
                alert.false_positive = True
                alert.false_positive_by = "auto-suppressed"
                alert.false_positive_at = datetime.now(timezone.utc)
                alert.resolved = True
                alert.resolved_at = datetime.now(timezone.utc)
                db.commit()
                suppressed = True
                break

        if suppressed:
            return

        to_emails = [e.strip() for e in (site.notification_emails or "").split(",") if e.strip()]

        try:
            await send_alert(
                channel=enum_val(site.notification_channel, "email"),
                to_emails=to_emails,
                site_name=site.name,
                status=status_str,
                message=message,
            )
        except Exception as ne:
            logger.error(f"Notification failed for {site.name}: {ne}")

    except Exception as e:
        logger.error(f"ALERT CREATION FAILED for {site.name}: {e}", exc_info=True)


async def _handle_slow_sites(db: Session) -> None:
    """Check all sites for sustained slowness and send ONE consolidated alert."""
    slow_sites = []

    sites = db.query(Site).filter(Site.is_active == True).all()
    for site in sites:
        threshold = site.slow_threshold_ms or 10000

        # Get latest result
        latest = (
            db.query(MonitoringResult)
            .filter(MonitoringResult.site_id == site.id)
            .order_by(MonitoringResult.checked_at.desc())
            .first()
        )
        if not latest or enum_val(latest.status, "") != "ok":
            continue

        response_time = latest.response_time_ms or 0
        if response_time <= threshold:
            continue

        # Site is currently slow — check if sustained
        if not _is_sustained_slowness(db, site.id, threshold):
            continue

        # Check 3-hour cooldown
        if _slow_alert_on_cooldown(db, site.id):
            logger.info(f"Slow alert for {site.name} on cooldown (sent within last {SLOW_COOLDOWN_HOURS}h)")
            continue

        slow_sites.append({
            "site": site,
            "response_ms": int(response_time),
            "threshold_ms": threshold,
        })

    if not slow_sites:
        return

    # Create or update alert records — one per site, no duplicates
    new_alerts = []
    for entry in slow_sites:
        site = entry["site"]
        msg = f"SLOW: {site.name} — {entry['response_ms']}ms (threshold: {entry['threshold_ms']}ms)"

        existing = (
            db.query(Alert)
            .filter(Alert.site_id == site.id, Alert.resolved == False)
            .first()
        )
        if existing:
            # Update existing alert message with latest data
            existing.message = msg
            existing.alert_type = "warning"
        else:
            alert = Alert(
                site_id=site.id,
                alert_type="warning",
                message=msg,
                notified=True,
                notified_at=datetime.now(timezone.utc),
                resolved=False,
            )
            db.add(alert)
            new_alerts.append(entry)

    db.commit()

    # Only send notification for NEW slow alerts (not already-existing ones)
    if not new_alerts:
        logger.info("All slow sites already have active alerts — skipping notification")
        return

    site_lines = "\n".join(
        f"- {e['site'].name} ({e['site'].url}): {e['response_ms']}ms (threshold: {e['threshold_ms']}ms)"
        for e in new_alerts
    )
    consolidated_msg = (
        f"{len(new_alerts)} site(s) experiencing sustained slowness "
        f"(>{SLOW_SUSTAINED_MINUTES} min):\n{site_lines}"
    )

    html_lines = "".join(
        f"<li><strong>{e['site'].name}</strong> — {e['response_ms']}ms (threshold: {e['threshold_ms']}ms)</li>"
        for e in new_alerts
    )
    html_msg = f"<p>{len(new_alerts)} site(s) with sustained slowness:</p><ul>{html_lines}</ul>"

    first_site = new_alerts[0]["site"]
    to_emails = [e.strip() for e in (first_site.notification_emails or "").split(",") if e.strip()]

    try:
        await send_alert(
            channel=first_enum_val(site.notification_channel, "email"),
            to_emails=to_emails,
            site_name="Multiple Sites",
            status="warning",
            message=html_msg,
        )
        logger.info(f"Consolidated slow alert sent for {len(slow_sites)} sites")
    except Exception as e:
        logger.error(f"Failed to send consolidated slow alert: {e}")


async def evaluate_and_alert(db: Session, result: MonitoringResult) -> None:
    try:
        site = db.query(Site).filter(Site.id == result.site_id).first()
        if not site:
            return

        logger.info(
            f"evaluate_and_alert: site={site.name}, status={enum_val(result.status, "critical")}, "
            f"code={result.status_code}, response={result.response_time_ms}ms"
        )

        result_status = enum_val(result.status, "critical")

        if result_status == "ok":
            slow_threshold = site.slow_threshold_ms or 10000
            response_time = result.response_time_ms or 0

            if response_time > slow_threshold:
                # Don't alert immediately — let _handle_slow_sites do consolidated alerting
                logger.info(f"Site {site.name} slow ({int(response_time)}ms) — consolidated check will handle")
                # Still run the consolidated check
                await _handle_slow_sites(db)
                return

            # Site OK and fast — resolve open alerts
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
                        channel=enum_val(site.notification_channel, "email"),
                        to_emails=(site.notification_emails or "").split(","),
                        site_name=site.name,
                        status="ok",
                        message=f"{site.name} ({site.url}) is back online. Response: {int(response_time)}ms",
                    )
                except Exception as e:
                    logger.error(f"Recovery alert failed for {site.name}: {e}")
            db.commit()
            return

        # Non-OK status — immediate alert
        if _is_immediate_alert(result):
            error_msg = f"HTTP {result.status_code} error on {site.name} ({site.url}). {result.error_message or ''}".strip()
        else:
            error_msg = result.error_message or f"Site {site.name} ({site.url}) is {enum_val(result.status, "critical")}."

        logger.warning(f"Alert: {site.name} — {enum_val(result.status, "critical")} — {error_msg[:100]}")
        await _create_and_send_alert(db, site, result, error_msg)

    except Exception as e:
        logger.error(f"evaluate_and_alert failed for site_id={result.site_id}: {e}", exc_info=True)
