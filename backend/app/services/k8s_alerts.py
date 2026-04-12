"""
Kubernetes Alert Evaluation
Analyzes snapshots and creates/resolves alerts based on rules.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.k8s_models import K8sAlert, K8sCluster, K8sSnapshot
from app.services.notification_service import send_alert

logger = logging.getLogger(__name__)

# Alert rules: (check_fn, alert_type, severity)
HIGH_CPU_THRESHOLD = 85
HIGH_MEMORY_THRESHOLD = 85
HIGH_RESTART_THRESHOLD = 5


async def evaluate_k8s_alerts(db: Session, cluster: K8sCluster, snapshot: K8sSnapshot):
    """Evaluate snapshot data and create/resolve alerts."""
    new_issues = []

    # Rule 1: Node NotReady
    for node in (snapshot.nodes_data or []):
        if node.get("status") != "Ready":
            new_issues.append({
                "alert_type": "node_not_ready",
                "severity": "critical",
                "resource_name": node["name"],
                "namespace": "",
                "message": f"[NODE] {node['name']} is NotReady | Conditions: {node.get('conditions', {})}",
            })

    # Rule 2: Pod CrashLoopBackOff
    for pod in (snapshot.pods_data or []):
        if pod.get("crash_loop"):
            new_issues.append({
                "alert_type": "pod_crash_loop",
                "severity": "critical",
                "resource_name": pod["name"],
                "namespace": pod.get("namespace", ""),
                "message": f"[POD] {pod['namespace']}/{pod['name']} is in CrashLoopBackOff | Restarts: {pod.get('restarts', 0)} | Node: {pod.get('node', '')}",
            })

    # Rule 3: Failed pods
    for pod in (snapshot.pods_data or []):
        if pod.get("status") == "Failed":
            new_issues.append({
                "alert_type": "pod_failed",
                "severity": "critical",
                "resource_name": pod["name"],
                "namespace": pod.get("namespace", ""),
                "message": f"[POD] {pod['namespace']}/{pod['name']} has Failed status | Node: {pod.get('node', '')}",
            })

    # Rule 4: High restart count
    for pod in (snapshot.pods_data or []):
        if pod.get("restarts", 0) >= HIGH_RESTART_THRESHOLD and not pod.get("crash_loop"):
            new_issues.append({
                "alert_type": "pod_high_restarts",
                "severity": "warning",
                "resource_name": pod["name"],
                "namespace": pod.get("namespace", ""),
                "message": f"[POD] {pod['namespace']}/{pod['name']} has {pod['restarts']} restarts | Node: {pod.get('node', '')}",
            })

    # Rule 5: High node CPU
    for node in (snapshot.nodes_data or []):
        cpu_pct = node.get("cpu_pct", 0)
        if cpu_pct > HIGH_CPU_THRESHOLD:
            new_issues.append({
                "alert_type": "node_high_cpu",
                "severity": "warning" if cpu_pct < 95 else "critical",
                "resource_name": node["name"],
                "namespace": "",
                "message": f"[NODE] {node['name']} CPU at {cpu_pct}% | Used: {node.get('cpu_used', 0)} / {node.get('cpu_capacity', 0)} cores",
            })

    # Rule 6: High node memory
    for node in (snapshot.nodes_data or []):
        mem_pct = node.get("memory_pct", 0)
        if mem_pct > HIGH_MEMORY_THRESHOLD:
            new_issues.append({
                "alert_type": "node_high_memory",
                "severity": "warning" if mem_pct < 95 else "critical",
                "resource_name": node["name"],
                "namespace": "",
                "message": f"[NODE] {node['name']} Memory at {mem_pct}% | Used: {node.get('memory_used_gb', 0):.1f} / {node.get('memory_capacity_gb', 0):.1f} GB",
            })

    # Rule 7: Pending pods (stuck)
    pending = [p for p in (snapshot.pods_data or []) if p.get("status") == "Pending"]
    if len(pending) > 3:
        names = ", ".join(p["name"] for p in pending[:5])
        new_issues.append({
            "alert_type": "pods_pending",
            "severity": "warning",
            "resource_name": f"{len(pending)} pods",
            "namespace": "",
            "message": f"[CLUSTER] {len(pending)} pods stuck in Pending state | {names}",
        })

    # Rule 8: Cluster connection failure
    if snapshot.cluster_status == "critical" and snapshot.error_message:
        new_issues.append({
            "alert_type": "cluster_unreachable",
            "severity": "critical",
            "resource_name": cluster.name,
            "namespace": "",
            "message": f"[CLUSTER] {cluster.name} is unreachable | {snapshot.error_message[:200]}",
        })

    # --- Create new alerts, resolve old ones ---
    # Get current active alerts for this cluster
    active_alerts = (
        db.query(K8sAlert)
        .filter(K8sAlert.cluster_id == cluster.id, K8sAlert.resolved == False)
        .all()
    )
    active_keys = {(a.alert_type, a.resource_name) for a in active_alerts}
    new_keys = {(i["alert_type"], i["resource_name"]) for i in new_issues}

    # Resolve alerts that are no longer present
    for alert in active_alerts:
        key = (alert.alert_type, alert.resource_name)
        if key not in new_keys:
            alert.resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
            logger.info(f"K8s alert resolved: {alert.alert_type} {alert.resource_name}")

    # Create alerts for new issues
    notifications = []
    for issue in new_issues:
        key = (issue["alert_type"], issue["resource_name"])
        if key not in active_keys:
            alert = K8sAlert(
                cluster_id=cluster.id,
                alert_type=issue["alert_type"],
                severity=issue["severity"],
                resource_name=issue["resource_name"],
                namespace=issue["namespace"],
                message=issue["message"],
            )
            db.add(alert)
            notifications.append(issue)
            logger.warning(f"K8s alert created: {issue['alert_type']} {issue['resource_name']}")

    db.commit()

    # Send notifications for new critical alerts
    critical_new = [n for n in notifications if n["severity"] == "critical"]
    if critical_new:
        msg_lines = "\n".join(f"- {n['message']}" for n in critical_new)
        try:
            await send_alert(
                channel="both",
                to_emails=[],
                site_name=f"K8s: {cluster.name}",
                status="critical",
                message=f"Kubernetes alerts on {cluster.name} ({cluster.cloud_provider}/{cluster.environment}):\n{msg_lines}",
            )
        except Exception as e:
            logger.error(f"K8s alert notification failed: {e}")
