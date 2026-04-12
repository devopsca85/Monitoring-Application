from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Alert, AlertStatus, FalsePositiveRule, MonitoringResult, Site, User
from app.models.schemas import (
    AlertDetailResponse,
    AlertResponse,
    DashboardStats,
    MonitoringResultCreate,
    MonitoringResultResponse,
)
from app.routes.auth import get_current_user
from app.services.alert_service import evaluate_and_alert
from app.services.scheduler_service import trigger_check_for_site

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.post("/results", response_model=MonitoringResultResponse, status_code=201)
async def submit_result(
    result_in: MonitoringResultCreate,
    db: Session = Depends(get_db),
):
    """Called by the monitoring engine to submit check results."""
    import logging
    logger = logging.getLogger(__name__)

    result = MonitoringResult(**result_in.model_dump())
    db.add(result)
    db.commit()
    db.refresh(result)

    logger.info(
        f"Result submitted: site_id={result.site_id}, status={result.status}, "
        f"code={result.status_code}, error={result.error_message or 'none'}"
    )

    try:
        await evaluate_and_alert(db, result)
    except Exception as e:
        logger.error(f"evaluate_and_alert failed: {e}")

    return result


@router.post("/trigger/{site_id}")
async def trigger_check(
    site_id: int,
    user: User = Depends(get_current_user),
):
    """Manually trigger a monitoring check for a site."""
    result = await trigger_check_for_site(site_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/results/{site_id}", response_model=list[MonitoringResultResponse])
def get_results(
    site_id: int,
    limit: int = Query(default=50, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(MonitoringResult)
        .filter(MonitoringResult.site_id == site_id)
        .order_by(MonitoringResult.checked_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/alerts", response_model=list[AlertDetailResponse])
def get_alerts(
    resolved: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    alerts = (
        db.query(Alert)
        .filter(Alert.resolved == resolved)
        .order_by(Alert.created_at.desc())
        .limit(100)
        .all()
    )
    site_ids = {a.site_id for a in alerts}
    sites = {s.id: s for s in db.query(Site).filter(Site.id.in_(site_ids)).all()} if site_ids else {}

    return [
        AlertDetailResponse(
            id=a.id,
            site_id=a.site_id,
            site_name=sites[a.site_id].name if a.site_id in sites else f"Site #{a.site_id}",
            site_url=sites[a.site_id].url if a.site_id in sites else "",
            alert_type=a.alert_type.value if a.alert_type and hasattr(a.alert_type, 'value') else (str(a.alert_type) if a.alert_type else None),
            message=a.message or "",
            notified=bool(a.notified) if a.notified is not None else False,
            resolved=bool(a.resolved) if a.resolved is not None else False,
            created_at=a.created_at,
            resolved_at=a.resolved_at,
        )
        for a in alerts
    ]


@router.get("/alert-history", response_model=list[AlertDetailResponse])
def get_alert_history(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """All alerts (active + resolved) with site name, ordered by newest first."""
    alerts = (
        db.query(Alert)
        .order_by(Alert.created_at.desc())
        .limit(limit)
        .all()
    )
    site_ids = {a.site_id for a in alerts}
    sites = {s.id: s for s in db.query(Site).filter(Site.id.in_(site_ids)).all()} if site_ids else {}

    result = []
    for a in alerts:
        s = sites.get(a.site_id)
        result.append(AlertDetailResponse(
            id=a.id,
            site_id=a.site_id,
            site_name=s.name if s else f"Site #{a.site_id}",
            site_url=s.url if s else "",
            alert_type=a.alert_type.value if a.alert_type and hasattr(a.alert_type, 'value') else (str(a.alert_type) if a.alert_type else None),
            message=a.message or "",
            notified=bool(a.notified) if a.notified is not None else False,
            resolved=bool(a.resolved) if a.resolved is not None else False,
            created_at=a.created_at,
            resolved_at=a.resolved_at,
        ))
    return result


def _cleanup_orphaned_alerts(db: Session):
    """Auto-resolve alerts whose site no longer exists."""
    from datetime import datetime, timezone
    valid_site_ids = {s.id for s in db.query(Site.id).all()}
    orphaned = (
        db.query(Alert)
        .filter(Alert.resolved == False)
        .all()
    )
    cleaned = 0
    for a in orphaned:
        if a.site_id not in valid_site_ids:
            a.resolved = True
            a.resolved_at = datetime.now(timezone.utc)
            a.message = (a.message or "") + " [Auto-resolved: site deleted]"
            cleaned += 1
    if cleaned:
        db.commit()
        import logging
        logging.getLogger(__name__).info(f"Cleaned up {cleaned} orphaned alerts")


def _to_iso_utc(dt):
    """Convert naive datetime to ISO string with UTC timezone marker."""
    if not dt:
        return None
    s = dt.isoformat()
    if '+' not in s and 'Z' not in s:
        s += '+00:00'
    return s


def _format_alert(a, sites_map):
    """Format an alert record as a plain dict."""
    s = sites_map.get(a.site_id)
    return {
        "id": a.id,
        "site_id": a.site_id,
        "site_name": s.name if s else f"(Deleted Site #{a.site_id})",
        "site_url": s.url if s else "",
        "alert_type": a.alert_type.value if a.alert_type and hasattr(a.alert_type, 'value') else str(a.alert_type or "critical"),
        "message": a.message or "",
        "notified": bool(a.notified or False),
        "resolved": bool(a.resolved or False),
        "false_positive": bool(a.false_positive or False),
        "false_positive_by": a.false_positive_by or "",
        "false_positive_at": _to_iso_utc(a.false_positive_at),
        "created_at": _to_iso_utc(a.created_at),
        "resolved_at": _to_iso_utc(a.resolved_at),
    }


@router.get("/alerts-raw")
def get_alerts_raw(
    resolved: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Returns alerts as plain dicts. Auto-cleans orphaned alerts."""
    _cleanup_orphaned_alerts(db)

    alerts = (
        db.query(Alert)
        .filter(Alert.resolved == resolved)
        .order_by(Alert.created_at.desc())
        .limit(100)
        .all()
    )

    # Only return alerts that have a valid site
    valid_site_ids = {s.id for s in db.query(Site.id).all()}
    alerts = [a for a in alerts if a.site_id in valid_site_ids]

    site_ids = {a.site_id for a in alerts}
    sites_map = {s.id: s for s in db.query(Site).filter(Site.id.in_(site_ids)).all()} if site_ids else {}

    return [_format_alert(a, sites_map) for a in alerts]


@router.get("/alert-history-raw")
def get_alert_history_raw(
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Returns all alert history as plain dicts. Filters out deleted sites."""
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(limit).all()
    valid_site_ids = {s.id for s in db.query(Site.id).all()}
    alerts = [a for a in alerts if a.site_id in valid_site_ids]
    site_ids = {a.site_id for a in alerts}
    sites_map = {s.id: s for s in db.query(Site).filter(Site.id.in_(site_ids)).all()} if site_ids else {}
    return [_format_alert(a, sites_map) for a in alerts]


@router.get("/alerts/debug")
def debug_alerts(db: Session = Depends(get_db)):
    """Debug endpoint — returns raw alert data without Pydantic serialization."""
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(20).all()
    return [
        {
            "id": a.id,
            "site_id": a.site_id,
            "alert_type": str(a.alert_type) if a.alert_type else None,
            "message": a.message,
            "notified": a.notified,
            "notified_type": type(a.notified).__name__,
            "resolved": a.resolved,
            "resolved_type": type(a.resolved).__name__,
            "created_at": str(a.created_at) if a.created_at else None,
            "resolved_at": str(a.resolved_at) if a.resolved_at else None,
        }
        for a in alerts
    ]


@router.get("/daily-report/preview")
def preview_daily_report(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Preview the daily report data (without sending)."""
    from app.services.daily_report import generate_daily_report
    return generate_daily_report(db)


@router.post("/daily-report/send")
async def trigger_daily_report(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually trigger the daily report email."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    from app.services.daily_report import send_daily_report
    await send_daily_report()
    return {"status": "Daily report sent"}


@router.delete("/alerts/history", status_code=200)
def delete_alert_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete all resolved alerts. Active alerts are not affected."""
    from app.routes.admin import require_admin
    # Only admins can delete history
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    deleted = db.query(Alert).filter(Alert.resolved == True).delete()
    db.commit()
    return {"status": f"Deleted {deleted} resolved alerts"}


@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/alerts/{alert_id}/false-positive")
def mark_false_positive(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark an alert as false positive + create suppression rule. Admin only."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can mark alerts as false positive")
    from datetime import datetime, timezone

    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.false_positive = True
    alert.false_positive_by = user.email
    alert.false_positive_at = datetime.now(timezone.utc)
    alert.resolved = True
    alert.resolved_at = datetime.now(timezone.utc)

    # Create a suppression rule from the error message
    # Extract the component tag [COMPONENT] as the pattern key
    error_msg = alert.message or ""
    pattern = error_msg
    if "]" in error_msg:
        # Use component + first part: "[LOGIN_AUTH] Password field still visible"
        bracket_end = error_msg.index("]") + 1
        first_pipe = error_msg.find("|")
        pattern = error_msg[:first_pipe].strip() if first_pipe > 0 else error_msg[:min(len(error_msg), 150)]
    else:
        pattern = error_msg[:150]

    # Check if rule already exists
    existing = (
        db.query(FalsePositiveRule)
        .filter(FalsePositiveRule.site_id == alert.site_id, FalsePositiveRule.error_pattern == pattern, FalsePositiveRule.is_active == True)
        .first()
    )
    if not existing:
        rule = FalsePositiveRule(
            site_id=alert.site_id,
            error_pattern=pattern,
            created_by=user.email,
        )
        db.add(rule)

    db.commit()
    return {"status": "Marked as false positive", "suppression_pattern": pattern}


@router.post("/alerts/{alert_id}/restore")
def restore_false_positive(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    """Restore a false positive alert and remove its suppression rule."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.false_positive = False
    alert.false_positive_by = None
    alert.false_positive_at = None
    alert.resolved = False
    alert.resolved_at = None

    # Deactivate matching suppression rules
    error_msg = alert.message or ""
    pattern = error_msg
    if "]" in error_msg:
        bracket_end = error_msg.index("]") + 1
        first_pipe = error_msg.find("|")
        pattern = error_msg[:first_pipe].strip() if first_pipe > 0 else error_msg[:150]
    else:
        pattern = error_msg[:150]

    rules = (
        db.query(FalsePositiveRule)
        .filter(FalsePositiveRule.site_id == alert.site_id, FalsePositiveRule.error_pattern == pattern)
        .all()
    )
    for r in rules:
        r.is_active = False

    db.commit()
    return {"status": "Alert restored, suppression rule deactivated"}


@router.get("/false-positives")
def get_false_positives(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all false positive alerts and active suppression rules."""
    fp_alerts = (
        db.query(Alert)
        .filter(Alert.false_positive == True)
        .order_by(Alert.false_positive_at.desc())
        .limit(100)
        .all()
    )
    valid_site_ids = {s.id for s in db.query(Site.id).all()}
    sites_map = {s.id: s for s in db.query(Site).all()}

    alerts_data = []
    for a in fp_alerts:
        if a.site_id not in valid_site_ids:
            continue
        s = sites_map.get(a.site_id)
        alerts_data.append({
            "id": a.id,
            "site_id": a.site_id,
            "site_name": s.name if s else f"Site #{a.site_id}",
            "alert_type": a.alert_type.value if a.alert_type and hasattr(a.alert_type, 'value') else str(a.alert_type or ""),
            "message": a.message or "",
            "false_positive_by": a.false_positive_by or "",
            "false_positive_at": _to_iso_utc(a.false_positive_at),
            "created_at": _to_iso_utc(a.created_at),
        })

    # Active suppression rules
    rules = (
        db.query(FalsePositiveRule)
        .filter(FalsePositiveRule.is_active == True)
        .order_by(FalsePositiveRule.created_at.desc())
        .all()
    )
    rules_data = []
    for r in rules:
        s = sites_map.get(r.site_id)
        rules_data.append({
            "id": r.id,
            "site_id": r.site_id,
            "site_name": s.name if s else f"Site #{r.site_id}",
            "error_pattern": r.error_pattern,
            "created_by": r.created_by or "",
            "created_at": _to_iso_utc(r.created_at),
        })

    return {"alerts": alerts_data, "rules": rules_data}


@router.delete("/false-positive-rules/{rule_id}")
def delete_fp_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a false positive suppression rule. Admin only."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    rule = db.query(FalsePositiveRule).filter(FalsePositiveRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return {"status": "Suppression rule deleted"}


@router.post("/alerts/acknowledge")
async def acknowledge_alerts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send Teams notification that alerts have been acknowledged."""
    from app.services.notification_service import send_teams_alert

    active = (
        db.query(Alert)
        .filter(Alert.resolved == False)
        .all()
    )
    valid_site_ids = {s.id for s in db.query(Site.id).all()}
    sites_map = {s.id: s for s in db.query(Site).all()}

    # Separate critical vs warning — alarm only fires for critical
    critical_names = []
    warning_names = []
    seen_critical = set()
    seen_warning = set()

    for a in active:
        if a.site_id not in valid_site_ids:
            continue
        s = sites_map.get(a.site_id)
        name = s.name if s else f"Site #{a.site_id}"
        is_critical = (a.alert_type == AlertStatus.CRITICAL or a.alert_type is None
                       or (hasattr(a.alert_type, 'value') and a.alert_type.value == 'critical'))

        if is_critical and a.site_id not in seen_critical:
            critical_names.append(name)
            seen_critical.add(a.site_id)
        elif not is_critical and a.site_id not in seen_warning:
            warning_names.append(name)
            seen_warning.add(a.site_id)

    if not critical_names and not warning_names:
        return {"status": "No active alerts to acknowledge"}

    parts = []
    if critical_names:
        parts.append(f"**Down:** {', '.join(critical_names)}")
    if warning_names:
        parts.append(f"**Slow/Warning:** {', '.join(warning_names)}")

    msg = (
        f"**Alert Acknowledged** by **{user.full_name or user.email}**\n\n"
        f"{chr(10).join(parts)}\n\n"
        f"The team is aware and actively investigating."
    )

    total = len(critical_names) + len(warning_names)
    title_parts = []
    if critical_names:
        title_parts.append(f"{len(critical_names)} down")
    if warning_names:
        title_parts.append(f"{len(warning_names)} slow")

    await send_teams_alert(
        title=f"Alert Acknowledged — {', '.join(title_parts)}",
        message=msg,
        color="007AFF",
    )

    return {"status": f"Acknowledge notification sent for {total} site(s)"}


@router.get("/sites-status")
def sites_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return all sites with their latest check result and next-check countdown."""
    sites = db.query(Site).all()

    latest_subq = (
        db.query(
            MonitoringResult.site_id,
            func.max(MonitoringResult.checked_at).label("max_checked"),
        )
        .group_by(MonitoringResult.site_id)
        .subquery()
    )
    latest_results = (
        db.query(MonitoringResult)
        .join(
            latest_subq,
            (MonitoringResult.site_id == latest_subq.c.site_id)
            & (MonitoringResult.checked_at == latest_subq.c.max_checked),
        )
        .all()
    )
    result_map = {r.site_id: r for r in latest_results}

    out = []
    for s in sites:
        r = result_map.get(s.id)
        out.append({
            "id": s.id,
            "name": s.name,
            "url": s.url,
            "check_type": s.check_type.value if s.check_type and hasattr(s.check_type, 'value') else str(s.check_type or "uptime"),
            "tech_stack": (s.tech_stack.value if hasattr(s.tech_stack, 'value') else str(s.tech_stack)) if s.tech_stack else "other",
            "check_interval_minutes": s.check_interval_minutes or 5,
            "slow_threshold_ms": s.slow_threshold_ms or 10000,
            "is_active": bool(s.is_active) if s.is_active is not None else True,
            "last_status": r.status.value if r and r.status and hasattr(r.status, 'value') else (str(r.status) if r and r.status else None),
            "last_checked_at": _to_iso_utc(r.checked_at) if r else None,
            "last_response_time_ms": r.response_time_ms if r else None,
            "is_slow": (r.response_time_ms or 0) > (s.slow_threshold_ms or 10000) if r else False,
            "last_status_code": r.status_code if r else None,
            "last_error": r.error_message if r else None,
        })
    return out


@router.get("/iis-diagnostics/{site_id}")
def iis_diagnostics(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Analyze recent monitoring results for IIS/App Pool issues and generate recommendations."""
    import json as json_mod
    from datetime import datetime, timedelta, timezone

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)

    # Get results from last 24 hours
    results_24h = (
        db.query(MonitoringResult)
        .filter(MonitoringResult.site_id == site_id, MonitoringResult.checked_at >= cutoff_24h)
        .order_by(MonitoringResult.checked_at.desc())
        .all()
    )

    # Get results from last 7 days for trend analysis
    results_7d = (
        db.query(MonitoringResult)
        .filter(MonitoringResult.site_id == site_id, MonitoringResult.checked_at >= cutoff_7d)
        .order_by(MonitoringResult.checked_at.desc())
        .all()
    )

    if not results_24h:
        return {"site_name": site.name, "has_issues": False, "message": "No recent data"}

    threshold = site.slow_threshold_ms or 10000
    total_checks = len(results_24h)
    failures = [r for r in results_24h if r.status != AlertStatus.OK]
    slow_checks = [r for r in results_24h if (r.response_time_ms or 0) > threshold]
    response_times = [r.response_time_ms or 0 for r in results_24h if r.response_time_ms]

    # === DETAILED FAILURE BREAKDOWN ===
    failure_types = {
        "login_failure": [], "http_error": [], "timeout": [],
        "db_issue": [], "error_page_redirect": [], "iis_issue": [],
        "subpage_failure": [], "other": [],
    }
    iis_issues_found = []
    cold_start_count = 0
    error_page_count = 0
    # Perf aggregations
    ttfb_values = []
    backend_pct_values = []
    slow_resources_all = {}
    slow_apis_all = {}
    failed_resources_all = {}
    bottleneck_counts = {"backend/database": 0, "frontend/rendering": 0}

    for r in results_24h:
        rt = r.response_time_ms or 0
        err = (r.error_message or "").lower()

        # Classify failure type
        if r.status != AlertStatus.OK:
            entry = {
                "time": _to_iso_utc(r.checked_at),
                "response_ms": int(rt),
                "error": (r.error_message or "")[:200],
                "status_code": r.status_code,
            }
            if "database issue" in err or "sql" in err or "db " in err:
                failure_types["db_issue"].append(entry)
            elif "login failed" in err or "password field" in err or "login page error" in err:
                failure_types["login_failure"].append(entry)
            elif "http 4" in err or "http 5" in err:
                failure_types["http_error"].append(entry)
            elif "timeout" in err or "timed out" in err:
                failure_types["timeout"].append(entry)
            elif "application error" in err or "genericerror" in err or "error page" in err:
                failure_types["error_page_redirect"].append(entry)
            elif "redirected to" in err or "element" in err and "not found" in err:
                failure_types["subpage_failure"].append(entry)
            else:
                failure_types["other"].append(entry)

        # Parse details JSON for perf data
        if not r.details:
            continue
        try:
            details = json_mod.loads(r.details)
            perf = details.get("perf", {})

            # IIS diagnostics
            for issue in perf.get("iis_diagnostics", []):
                iis_issues_found.append({
                    "time": _to_iso_utc(r.checked_at),
                    "category": issue.get("category", ""),
                    "severity": issue.get("severity", ""),
                    "diagnosis": issue.get("diagnosis", ""),
                    "recommendation": issue.get("recommendation", ""),
                })
                if issue.get("category") == "cold_start":
                    cold_start_count += 1
                if r.status != AlertStatus.OK:
                    failure_types["iis_issue"].append({
                        "time": _to_iso_utc(r.checked_at),
                        "response_ms": int(rt),
                        "error": issue.get("diagnosis", "")[:200],
                        "category": issue.get("category", ""),
                    })

            if details.get("error_page_redirect"):
                error_page_count += 1

            # Aggregate perf metrics
            ttfb = perf.get("ttfb_ms", 0)
            if ttfb > 0:
                ttfb_values.append(ttfb)
            bpct = perf.get("backend_time_pct", 0)
            if bpct > 0:
                backend_pct_values.append(bpct)
            bn = perf.get("bottleneck", "")
            if bn in bottleneck_counts:
                bottleneck_counts[bn] += 1

            # Aggregate slow resources across checks
            for sr in perf.get("slow_resources", []):
                name = sr.get("name", "unknown")
                slow_resources_all.setdefault(name, []).append(sr.get("duration", 0))
            for sa in perf.get("slow_api_calls", []):
                url = sa.get("url", "unknown")
                slow_apis_all.setdefault(url, []).append(sa.get("duration", 0))
            for fr in perf.get("failed_resources", []):
                name = fr.get("name", "unknown")
                failed_resources_all[name] = failed_resources_all.get(name, 0) + 1
        except Exception:
            pass

    # === SLOWNESS ROOT CAUSE ANALYSIS ===
    slowness_causes = []
    if backend_pct_values:
        avg_backend = round(sum(backend_pct_values) / len(backend_pct_values))
        if avg_backend > 60:
            slowness_causes.append({
                "cause": "Backend / Server Processing",
                "detail": f"Average {avg_backend}% of load time is server-side (TTFB). Likely database queries or application logic.",
                "severity": "high" if avg_backend > 80 else "medium",
            })
    if bottleneck_counts["frontend/rendering"] > 3:
        slowness_causes.append({
            "cause": "Frontend / JS Rendering",
            "detail": f"{bottleneck_counts['frontend/rendering']} checks flagged frontend rendering as bottleneck. Heavy JS bundles or client-side processing.",
            "severity": "medium",
        })

    # Top slow resources
    top_slow_resources = sorted(
        [{"name": k, "avg_ms": round(sum(v)/len(v)), "occurrences": len(v)} for k, v in slow_resources_all.items()],
        key=lambda x: x["avg_ms"], reverse=True,
    )[:10]
    if top_slow_resources:
        slowness_causes.append({
            "cause": "Slow Static Resources",
            "detail": f"{len(top_slow_resources)} resources consistently slow. Top: {top_slow_resources[0]['name']} ({top_slow_resources[0]['avg_ms']}ms avg)",
            "severity": "medium",
            "resources": top_slow_resources,
        })

    # Top slow API calls
    top_slow_apis = sorted(
        [{"url": k, "avg_ms": round(sum(v)/len(v)), "occurrences": len(v)} for k, v in slow_apis_all.items()],
        key=lambda x: x["avg_ms"], reverse=True,
    )[:10]
    if top_slow_apis:
        slowness_causes.append({
            "cause": "Slow Backend API Calls",
            "detail": f"{len(top_slow_apis)} API endpoints consistently slow. Top: {top_slow_apis[0]['url']} ({top_slow_apis[0]['avg_ms']}ms avg)",
            "severity": "high",
            "apis": top_slow_apis,
        })

    # Failed resources
    top_failed = sorted(
        [{"name": k, "count": v} for k, v in failed_resources_all.items()],
        key=lambda x: x["count"], reverse=True,
    )[:10]

    # === 7-DAY TREND ===
    daily_failures = {}
    daily_slow = {}
    for r in results_7d:
        if r.checked_at:
            day = r.checked_at.strftime("%Y-%m-%d")
            if r.status != AlertStatus.OK:
                daily_failures[day] = daily_failures.get(day, 0) + 1
            if (r.response_time_ms or 0) > threshold:
                daily_slow[day] = daily_slow.get(day, 0) + 1

    # === RECOMMENDATIONS ===
    recommendations = []

    if cold_start_count >= 3:
        recommendations.append({
            "priority": "high", "category": "App Pool Cold Start",
            "issue": f"{cold_start_count} cold start patterns in 24h",
            "actions": [
                "Set Start Mode to 'AlwaysRunning'", "Enable preloadEnabled=true",
                "Configure Warm-Up module", "Set Idle Timeout to 0",
            ],
        })

    if len(failures) > 5 and len(failures) / total_checks > 0.1:
        top_type = max(failure_types.items(), key=lambda x: len(x[1]))
        recommendations.append({
            "priority": "high", "category": "App Pool Stability",
            "issue": f"{len(failures)}/{total_checks} failures ({round(len(failures)/total_checks*100)}%). Primary: {top_type[0]} ({len(top_type[1])})",
            "actions": [
                "Check Event Viewer for W3WP crash events",
                "Review Rapid-Fail Protection settings",
                "Increase Private Memory Limit",
                "Check Application Event Log for unhandled exceptions",
            ],
        })

    if len(slow_checks) > 5 and len(slow_checks) / total_checks > 0.2:
        avg_slow = sum(r.response_time_ms or 0 for r in slow_checks) / len(slow_checks)
        primary_cause = slowness_causes[0]["cause"] if slowness_causes else "Unknown"
        recommendations.append({
            "priority": "medium", "category": "Performance",
            "issue": f"{len(slow_checks)} slow ({round(len(slow_checks)/total_checks*100)}%, avg {int(avg_slow)}ms). Primary cause: {primary_cause}",
            "actions": [
                "Profile database queries for slow operations",
                "Enable IIS output caching and compression",
                "Increase maxConcurrentRequestsPerCPU",
                "Consider Web Garden for CPU-bound workloads",
            ],
        })

    if error_page_count >= 3:
        recommendations.append({
            "priority": "high", "category": "Application Errors",
            "issue": f"{error_page_count} error page redirects in 24h",
            "actions": [
                "Check Application Event Log", "Review customErrors in web.config",
                "Enable detailed errors temporarily", "Correlate with deployment times",
            ],
        })

    if len(daily_failures) >= 3:
        days_sorted = sorted(daily_failures.items())
        if len(days_sorted) >= 3:
            recent = sum(v for _, v in days_sorted[-3:]) / 3
            older = sum(v for _, v in days_sorted[:max(1, len(days_sorted)-3)]) / max(1, len(days_sorted)-3)
            if recent > older * 1.5 and recent > 2:
                recommendations.append({
                    "priority": "medium", "category": "Worsening Trend",
                    "issue": f"Failures increasing: recent {recent:.0f}/day vs earlier {older:.0f}/day",
                    "actions": [
                        "Investigate recent deployments", "Check server resource trends",
                        "Review IIS logs", "Consider scaling",
                    ],
                })

    # Filter out empty failure types
    failure_breakdown = {k: v for k, v in failure_types.items() if v}

    return {
        "site_name": site.name,
        "site_url": site.url,
        "has_issues": len(recommendations) > 0 or len(failure_breakdown) > 0,
        "summary": {
            "checks_24h": total_checks,
            "failures_24h": len(failures),
            "slow_24h": len(slow_checks),
            "ok_24h": total_checks - len(failures),
            "failure_rate": round(len(failures) / max(total_checks, 1) * 100, 1),
            "avg_response_ms": round(sum(response_times) / max(len(response_times), 1)),
            "avg_ttfb_ms": round(sum(ttfb_values) / max(len(ttfb_values), 1)) if ttfb_values else 0,
            "avg_backend_pct": round(sum(backend_pct_values) / max(len(backend_pct_values), 1)) if backend_pct_values else 0,
            "cold_starts": cold_start_count,
            "error_pages": error_page_count,
            "bottleneck_backend": bottleneck_counts.get("backend/database", 0),
            "bottleneck_frontend": bottleneck_counts.get("frontend/rendering", 0),
        },
        "failure_breakdown": failure_breakdown,
        "slowness_causes": slowness_causes,
        "top_slow_resources": top_slow_resources,
        "top_slow_apis": top_slow_apis,
        "top_failed_resources": top_failed,
        "recommendations": recommendations,
        "iis_issues_detected": iis_issues_found[:20],
        "daily_trend": [
            {"date": d, "failures": daily_failures.get(d, 0), "slow": daily_slow.get(d, 0)}
            for d in sorted(set(list(daily_failures.keys()) + list(daily_slow.keys())))
        ],
    }


@router.get("/slowness-analysis")
def slowness_analysis(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Returns sites that were slow for >60 minutes in the last 24 hours, with time windows."""
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    sites = db.query(Site).filter(Site.is_active == True).all()
    result = []

    for site in sites:
        threshold = site.slow_threshold_ms or 10000

        # Get all results for this site in the last 24h
        results = (
            db.query(MonitoringResult)
            .filter(
                MonitoringResult.site_id == site.id,
                MonitoringResult.checked_at >= cutoff,
            )
            .order_by(MonitoringResult.checked_at.asc())
            .all()
        )

        if not results:
            continue

        # Find slow windows (consecutive slow results)
        slow_windows = []
        window_start = None
        window_results = []

        for r in results:
            rt = r.response_time_ms or 0
            if rt > threshold:
                if window_start is None:
                    window_start = r.checked_at
                window_results.append(r)
            else:
                if window_start and window_results:
                    window_end = window_results[-1].checked_at
                    duration_min = (window_end - window_start).total_seconds() / 60
                    if duration_min >= 60:
                        avg_rt = sum(wr.response_time_ms or 0 for wr in window_results) / len(window_results)
                        max_rt = max(wr.response_time_ms or 0 for wr in window_results)
                        slow_windows.append({
                            "start": _to_iso_utc(window_start),
                            "end": _to_iso_utc(window_end),
                            "duration_minutes": round(duration_min),
                            "check_count": len(window_results),
                            "avg_response_ms": round(avg_rt),
                            "max_response_ms": round(max_rt),
                        })
                window_start = None
                window_results = []

        # Handle ongoing slow window
        if window_start and window_results:
            window_end = window_results[-1].checked_at
            duration_min = (window_end - window_start).total_seconds() / 60
            if duration_min >= 60:
                avg_rt = sum(wr.response_time_ms or 0 for wr in window_results) / len(window_results)
                max_rt = max(wr.response_time_ms or 0 for wr in window_results)
                slow_windows.append({
                    "start": _to_iso_utc(window_start),
                    "end": _to_iso_utc(window_end),
                    "duration_minutes": round(duration_min),
                    "check_count": len(window_results),
                    "avg_response_ms": round(avg_rt),
                    "max_response_ms": round(max_rt),
                    "ongoing": True,
                })

        if slow_windows:
            # Build hourly response time data for the chart
            hourly = {}
            for r in results:
                if r.checked_at:
                    hour_key = r.checked_at.strftime("%Y-%m-%d %H:00")
                    if hour_key not in hourly:
                        hourly[hour_key] = []
                    hourly[hour_key].append(r.response_time_ms or 0)

            hourly_data = [
                {"hour": k, "avg_ms": round(sum(v) / len(v)), "max_ms": round(max(v)), "count": len(v)}
                for k, v in sorted(hourly.items())
            ]

            total_slow_min = sum(w["duration_minutes"] for w in slow_windows)
            result.append({
                "site_id": site.id,
                "site_name": site.name,
                "site_url": site.url,
                "threshold_ms": threshold,
                "slow_windows": slow_windows,
                "total_slow_minutes": total_slow_min,
                "hourly_data": hourly_data,
            })

    # Sort by total slow time descending
    result.sort(key=lambda x: x["total_slow_minutes"], reverse=True)
    return result


@router.get("/dashboard", response_model=DashboardStats)
def dashboard_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total = db.query(Site).filter(Site.is_active == True).count()

    # Get latest result per site using a subquery
    latest_subq = (
        db.query(
            MonitoringResult.site_id,
            func.max(MonitoringResult.checked_at).label("max_checked"),
        )
        .group_by(MonitoringResult.site_id)
        .subquery()
    )

    latest_results = (
        db.query(MonitoringResult)
        .join(
            latest_subq,
            (MonitoringResult.site_id == latest_subq.c.site_id)
            & (MonitoringResult.checked_at == latest_subq.c.max_checked),
        )
        .all()
    )

    up = sum(1 for r in latest_results if r.status == AlertStatus.OK)
    down = sum(1 for r in latest_results if r.status == AlertStatus.CRITICAL)
    warning = sum(1 for r in latest_results if r.status == AlertStatus.WARNING)

    avg_rt = (
        sum(r.response_time_ms or 0 for r in latest_results) / len(latest_results)
        if latest_results
        else 0
    )

    return DashboardStats(
        total_sites=total,
        sites_up=up,
        sites_down=down,
        sites_warning=warning,
        avg_response_time=round(avg_rt, 2),
    )
