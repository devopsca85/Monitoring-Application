from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Alert, AlertStatus, MonitoringResult, Site, User
from app.models.schemas import (
    AlertResponse,
    DashboardStats,
    MonitoringResultCreate,
    MonitoringResultResponse,
)
from app.routes.auth import get_current_user
from app.services.alert_service import evaluate_and_alert

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.post("/results", response_model=MonitoringResultResponse, status_code=201)
async def submit_result(
    result_in: MonitoringResultCreate,
    db: Session = Depends(get_db),
):
    """Called by the monitoring engine to submit check results."""
    result = MonitoringResult(**result_in.model_dump())
    db.add(result)
    db.commit()
    db.refresh(result)

    await evaluate_and_alert(db, result)
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


@router.get("/alerts", response_model=list[AlertResponse])
def get_alerts(
    resolved: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Alert).filter(Alert.resolved == resolved)
    return query.order_by(Alert.created_at.desc()).limit(100).all()


@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    db.commit()
    db.refresh(alert)
    return alert


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
