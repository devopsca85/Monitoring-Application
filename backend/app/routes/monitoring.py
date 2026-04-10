from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Alert, AlertStatus, MonitoringResult, Site, User
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
        f"Result submitted: site_id={result.site_id}, status={result.status.value}, "
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
            "check_type": s.check_type.value,
            "check_interval_minutes": s.check_interval_minutes,
            "slow_threshold_ms": s.slow_threshold_ms or 10000,
            "is_active": s.is_active,
            "last_status": r.status.value if r else None,
            "last_checked_at": _to_iso_utc(r.checked_at) if r else None,
            "last_response_time_ms": r.response_time_ms if r else None,
            "is_slow": (r.response_time_ms or 0) > (s.slow_threshold_ms or 10000) if r else False,
            "last_status_code": r.status_code if r else None,
            "last_error": r.error_message if r else None,
        })
    return out


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
