"""
Kubernetes Monitoring API Routes
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import encrypt_credential
from app.models.k8s_models import K8sAlert, K8sCluster, K8sSnapshot
from app.models.models import User
from app.routes.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/k8s", tags=["kubernetes"])


def _safe(val, default=""):
    if val is None:
        return default
    return val.value if hasattr(val, 'value') else val


# --- Schemas ---
class ClusterCreate(BaseModel):
    name: str
    cloud_provider: str = "azure"
    environment: str = "production"
    region: str = ""
    api_server_url: str = ""
    auth_type: str = "kubeconfig"
    kubeconfig: str = ""
    token: str = ""
    namespace_filter: str = ""
    check_interval_minutes: int = 3


class ClusterUpdate(BaseModel):
    name: str | None = None
    cloud_provider: str | None = None
    environment: str | None = None
    region: str | None = None
    api_server_url: str | None = None
    auth_type: str | None = None
    kubeconfig: str | None = None
    token: str | None = None
    namespace_filter: str | None = None
    check_interval_minutes: int | None = None
    is_active: bool | None = None


# --- Cluster CRUD ---
@router.get("/clusters")
def list_clusters(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    clusters = db.query(K8sCluster).order_by(K8sCluster.name).all()
    result = []
    for c in clusters:
        # Get latest snapshot
        latest = (
            db.query(K8sSnapshot)
            .filter(K8sSnapshot.cluster_id == c.id)
            .order_by(K8sSnapshot.checked_at.desc())
            .first()
        )
        active_alerts = (
            db.query(K8sAlert)
            .filter(K8sAlert.cluster_id == c.id, K8sAlert.resolved == False)
            .count()
        )
        result.append({
            "id": c.id,
            "name": c.name,
            "cloud_provider": _safe(c.cloud_provider, "azure"),
            "environment": _safe(c.environment, "production"),
            "region": c.region or "",
            "is_active": bool(c.is_active),
            "check_interval_minutes": c.check_interval_minutes or 3,
            "status": latest.cluster_status if latest else "unknown",
            "total_nodes": latest.total_nodes if latest else 0,
            "ready_nodes": latest.ready_nodes if latest else 0,
            "total_pods": latest.total_pods if latest else 0,
            "running_pods": latest.running_pods if latest else 0,
            "failed_pods": latest.failed_pods if latest else 0,
            "cpu_pct": round(latest.cpu_used_cores / max(latest.cpu_capacity_cores, 0.01) * 100, 1) if latest and latest.cpu_capacity_cores else 0,
            "memory_pct": round(latest.memory_used_gb / max(latest.memory_capacity_gb, 0.01) * 100, 1) if latest and latest.memory_capacity_gb else 0,
            "active_alerts": active_alerts,
            "last_checked": latest.checked_at.isoformat() + "+00:00" if latest and latest.checked_at else None,
            "k8s_version": latest.k8s_version if latest else "",
        })
    return result


@router.post("/clusters", status_code=201)
def create_cluster(
    data: ClusterCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    cluster = K8sCluster(
        name=data.name,
        cloud_provider=data.cloud_provider,
        environment=data.environment,
        region=data.region,
        api_server_url=data.api_server_url,
        auth_type=data.auth_type,
        namespace_filter=data.namespace_filter,
        check_interval_minutes=data.check_interval_minutes,
    )
    if data.kubeconfig:
        cluster.encrypted_kubeconfig = encrypt_credential(data.kubeconfig)
    if data.token:
        cluster.encrypted_token = encrypt_credential(data.token)

    db.add(cluster)
    db.commit()
    return {"status": "Cluster added", "id": cluster.id}


@router.put("/clusters/{cluster_id}")
def update_cluster(
    cluster_id: int,
    data: ClusterUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    c = db.query(K8sCluster).filter(K8sCluster.id == cluster_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cluster not found")

    for field in ["name", "cloud_provider", "environment", "region", "api_server_url",
                   "auth_type", "namespace_filter", "check_interval_minutes", "is_active"]:
        val = getattr(data, field, None)
        if val is not None:
            setattr(c, field, val)
    if data.kubeconfig:
        c.encrypted_kubeconfig = encrypt_credential(data.kubeconfig)
    if data.token:
        c.encrypted_token = encrypt_credential(data.token)

    db.commit()
    return {"status": "Cluster updated"}


@router.delete("/clusters/{cluster_id}")
def delete_cluster(
    cluster_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    c = db.query(K8sCluster).filter(K8sCluster.id == cluster_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cluster not found")
    db.delete(c)
    db.commit()
    return {"status": "Cluster deleted"}


# --- Cluster Detail ---
@router.get("/clusters/{cluster_id}")
def get_cluster_detail(
    cluster_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.query(K8sCluster).filter(K8sCluster.id == cluster_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cluster not found")

    latest = (
        db.query(K8sSnapshot)
        .filter(K8sSnapshot.cluster_id == c.id)
        .order_by(K8sSnapshot.checked_at.desc())
        .first()
    )

    return {
        "id": c.id,
        "name": c.name,
        "cloud_provider": _safe(c.cloud_provider),
        "environment": _safe(c.environment),
        "region": c.region or "",
        "is_active": bool(c.is_active),
        "check_interval_minutes": c.check_interval_minutes or 3,
        "namespace_filter": c.namespace_filter or "",
        "auth_type": c.auth_type or "",
        "api_server_url": c.api_server_url or "",
        "has_kubeconfig": bool(c.encrypted_kubeconfig),
        "has_token": bool(c.encrypted_token),
        "snapshot": {
            "status": latest.cluster_status if latest else "unknown",
            "k8s_version": latest.k8s_version if latest else "",
            "checked_at": latest.checked_at.isoformat() + "+00:00" if latest and latest.checked_at else None,
            "total_nodes": latest.total_nodes if latest else 0,
            "ready_nodes": latest.ready_nodes if latest else 0,
            "total_pods": latest.total_pods if latest else 0,
            "running_pods": latest.running_pods if latest else 0,
            "failed_pods": latest.failed_pods if latest else 0,
            "pending_pods": latest.pending_pods if latest else 0,
            "cpu_capacity": latest.cpu_capacity_cores if latest else 0,
            "cpu_used": latest.cpu_used_cores if latest else 0,
            "memory_capacity_gb": latest.memory_capacity_gb if latest else 0,
            "memory_used_gb": latest.memory_used_gb if latest else 0,
            "nodes": latest.nodes_data if latest else [],
            "pods": latest.pods_data if latest else [],
            "events": latest.events_data if latest else [],
            "error": latest.error_message if latest else "",
        } if latest else None,
    }


# --- Alerts ---
@router.get("/clusters/{cluster_id}/alerts")
def get_cluster_alerts(
    cluster_id: int,
    resolved: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    alerts = (
        db.query(K8sAlert)
        .filter(K8sAlert.cluster_id == cluster_id, K8sAlert.resolved == resolved)
        .order_by(K8sAlert.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": a.id,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "resource_name": a.resource_name,
            "namespace": a.namespace or "",
            "message": a.message or "",
            "resolved": bool(a.resolved),
            "resolved_at": a.resolved_at.isoformat() + "+00:00" if a.resolved_at else None,
            "created_at": a.created_at.isoformat() + "+00:00" if a.created_at else None,
        }
        for a in alerts
    ]


@router.post("/clusters/{cluster_id}/alerts/{alert_id}/resolve")
def resolve_k8s_alert(
    cluster_id: int,
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    alert = db.query(K8sAlert).filter(K8sAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "Alert resolved"}


# --- History ---
@router.get("/clusters/{cluster_id}/history")
def get_cluster_history(
    cluster_id: int,
    hours: int = Query(default=24, le=168),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    snapshots = (
        db.query(K8sSnapshot)
        .filter(K8sSnapshot.cluster_id == cluster_id, K8sSnapshot.checked_at >= cutoff)
        .order_by(K8sSnapshot.checked_at.asc())
        .all()
    )
    return [
        {
            "checked_at": s.checked_at.isoformat() + "+00:00" if s.checked_at else None,
            "status": s.cluster_status,
            "nodes": s.total_nodes,
            "ready_nodes": s.ready_nodes,
            "pods": s.total_pods,
            "running_pods": s.running_pods,
            "failed_pods": s.failed_pods,
            "cpu_used": s.cpu_used_cores,
            "cpu_capacity": s.cpu_capacity_cores,
            "memory_used_gb": s.memory_used_gb,
            "memory_capacity_gb": s.memory_capacity_gb,
        }
        for s in snapshots
    ]
