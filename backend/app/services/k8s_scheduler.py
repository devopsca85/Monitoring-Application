"""
Kubernetes Monitoring Scheduler
Runs checks for all active K8s clusters on their configured intervals.
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.k8s_models import K8sCluster, K8sSnapshot
from app.services.k8s_collector import collect_cluster_snapshot
from app.services.k8s_alerts import evaluate_k8s_alerts

logger = logging.getLogger(__name__)

_k8s_task = None
_running: set[int] = set()


async def _check_cluster(cluster_id: int, last_checked: dict):
    """Run a single cluster check."""
    _running.add(cluster_id)
    db = SessionLocal()
    try:
        cluster = db.query(K8sCluster).filter(K8sCluster.id == cluster_id).first()
        if not cluster or not cluster.is_active:
            return

        logger.info(f"K8s check starting: {cluster.name}")
        data = collect_cluster_snapshot(cluster)

        snapshot = K8sSnapshot(
            cluster_id=cluster.id,
            cluster_status=data["cluster_status"],
            k8s_version=data.get("k8s_version", ""),
            total_nodes=data["total_nodes"],
            ready_nodes=data["ready_nodes"],
            total_pods=data["total_pods"],
            running_pods=data["running_pods"],
            failed_pods=data["failed_pods"],
            pending_pods=data["pending_pods"],
            cpu_capacity_cores=data.get("cpu_capacity_cores"),
            cpu_used_cores=data.get("cpu_used_cores"),
            memory_capacity_gb=data.get("memory_capacity_gb"),
            memory_used_gb=data.get("memory_used_gb"),
            nodes_data=data.get("nodes_data"),
            pods_data=data.get("pods_data"),
            events_data=data.get("events_data"),
            error_message=data.get("error_message", ""),
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        logger.info(f"K8s snapshot #{snapshot.id}: {cluster.name} — {data['cluster_status']} "
                     f"({data['ready_nodes']}/{data['total_nodes']} nodes, "
                     f"{data['running_pods']}/{data['total_pods']} pods)")

        await evaluate_k8s_alerts(db, cluster, snapshot)
        last_checked[cluster_id] = asyncio.get_event_loop().time()

    except Exception as e:
        logger.error(f"K8s check failed for cluster {cluster_id}: {e}", exc_info=True)
        last_checked.pop(cluster_id, None)
    finally:
        _running.discard(cluster_id)
        db.close()


async def _run_k8s_scheduler():
    """Background loop for K8s cluster monitoring."""
    logger.info("K8s monitoring scheduler started")
    last_checked: dict[int, float] = {}

    while True:
        try:
            db = SessionLocal()
            try:
                clusters = db.query(K8sCluster).filter(K8sCluster.is_active == True).all()
                cluster_data = [(c.id, c.check_interval_minutes, c.name) for c in clusters]
            finally:
                db.close()

            now = asyncio.get_event_loop().time()
            for cid, interval, name in cluster_data:
                interval_sec = (interval or 3) * 60
                last = last_checked.get(cid, 0)
                if now - last >= interval_sec and cid not in _running:
                    asyncio.create_task(_check_cluster(cid, last_checked))

        except Exception as e:
            logger.error(f"K8s scheduler loop error: {e}")

        await asyncio.sleep(30)


def start_k8s_scheduler():
    global _k8s_task
    _k8s_task = asyncio.create_task(_run_k8s_scheduler())
    logger.info("K8s monitoring scheduler initialized")


def stop_k8s_scheduler():
    global _k8s_task
    if _k8s_task:
        _k8s_task.cancel()
        _k8s_task = None
