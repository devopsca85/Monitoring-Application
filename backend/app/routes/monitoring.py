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
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
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
            "last_checked_at": r.checked_at.isoformat() if r and r.checked_at else None,
            "last_response_time_ms": r.response_time_ms if r else None,
            "is_slow": (r.response_time_ms or 0) > (s.slow_threshold_ms or 10000) if r else False,
            "last_status_code": r.status_code if r else None,
            "last_error": r.error_message if r else None,
        })
    return out


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
