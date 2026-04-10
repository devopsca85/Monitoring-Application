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
            alert_type=a.alert_type,
            message=a.message,
            notified=a.notified,
            resolved=a.resolved,
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
    sites = {s.id: s for s in db.query(Site).filter(Site.id.in_(site_ids)).all()}

    result = []
    for a in alerts:
        s = sites.get(a.site_id)
        result.append(AlertDetailResponse(
            id=a.id,
            site_id=a.site_id,
            site_name=s.name if s else f"Site #{a.site_id}",
            site_url=s.url if s else "",
            alert_type=a.alert_type,
            message=a.message,
            notified=a.notified,
            resolved=a.resolved,
            created_at=a.created_at,
            resolved_at=a.resolved_at,
        ))
    return result


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
