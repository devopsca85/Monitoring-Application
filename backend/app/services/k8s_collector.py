"""
Kubernetes Metrics Collector
Connects to K8s clusters via API and collects node, pod, and event data.
Uses the official kubernetes Python client.
"""
import logging
import tempfile
import os
from datetime import datetime, timezone

from app.core.security import decrypt_credential

logger = logging.getLogger(__name__)


def _get_k8s_client(cluster):
    """Create a Kubernetes API client from cluster config."""
    try:
        from kubernetes import client, config

        if cluster.auth_type == "kubeconfig" and cluster.encrypted_kubeconfig:
            kubeconfig_yaml = decrypt_credential(cluster.encrypted_kubeconfig)
            # Write to temp file for kubernetes client
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
            tmp.write(kubeconfig_yaml)
            tmp.close()
            try:
                config.load_kube_config(config_file=tmp.name)
            finally:
                os.unlink(tmp.name)

        elif cluster.auth_type == "token" and cluster.encrypted_token:
            token = decrypt_credential(cluster.encrypted_token)
            configuration = client.Configuration()
            configuration.host = cluster.api_server_url
            configuration.api_key = {"authorization": f"Bearer {token}"}
            configuration.verify_ssl = False  # For self-signed certs
            client.Configuration.set_default(configuration)

        elif cluster.api_server_url:
            configuration = client.Configuration()
            configuration.host = cluster.api_server_url
            configuration.verify_ssl = False
            client.Configuration.set_default(configuration)
        else:
            raise ValueError("No valid auth configuration found")

        return client.CoreV1Api(), client.AppsV1Api()

    except ImportError:
        logger.error("kubernetes package not installed. Run: pip install kubernetes")
        raise
    except Exception as e:
        logger.error(f"Failed to create K8s client for {cluster.name}: {e}")
        raise


def collect_cluster_snapshot(cluster) -> dict:
    """Collect a full snapshot of cluster state."""
    result = {
        "cluster_status": "healthy",
        "k8s_version": "",
        "total_nodes": 0, "ready_nodes": 0,
        "total_pods": 0, "running_pods": 0, "failed_pods": 0, "pending_pods": 0,
        "cpu_capacity_cores": 0, "cpu_used_cores": 0,
        "memory_capacity_gb": 0, "memory_used_gb": 0,
        "nodes_data": [], "pods_data": [], "events_data": [],
        "error_message": "",
    }

    try:
        core_api, apps_api = _get_k8s_client(cluster)
    except Exception as e:
        result["cluster_status"] = "critical"
        result["error_message"] = f"Connection failed: {str(e)[:200]}"
        return result

    namespace_filter = [n.strip() for n in (cluster.namespace_filter or "").split(",") if n.strip()]

    # --- Nodes ---
    try:
        nodes = core_api.list_node()
        result["total_nodes"] = len(nodes.items)

        nodes_data = []
        total_cpu_cap = 0
        total_mem_cap = 0

        for node in nodes.items:
            name = node.metadata.name
            conditions = {c.type: c.status for c in (node.status.conditions or [])}
            is_ready = conditions.get("Ready") == "True"
            if is_ready:
                result["ready_nodes"] += 1

            # Capacity
            cpu_cap = _parse_cpu(node.status.capacity.get("cpu", "0"))
            mem_cap = _parse_memory(node.status.capacity.get("memory", "0"))
            total_cpu_cap += cpu_cap
            total_mem_cap += mem_cap

            node_info = {
                "name": name,
                "status": "Ready" if is_ready else "NotReady",
                "cpu_capacity": round(cpu_cap, 2),
                "memory_capacity_gb": round(mem_cap, 2),
                "conditions": conditions,
                "os": node.status.node_info.os_image if node.status.node_info else "",
                "kubelet_version": node.status.node_info.kubelet_version if node.status.node_info else "",
            }
            nodes_data.append(node_info)

        result["nodes_data"] = nodes_data
        result["cpu_capacity_cores"] = round(total_cpu_cap, 2)
        result["memory_capacity_gb"] = round(total_mem_cap, 2)

        # Get version from first node
        if nodes.items:
            result["k8s_version"] = nodes.items[0].status.node_info.kubelet_version if nodes.items[0].status.node_info else ""

    except Exception as e:
        logger.error(f"Node collection failed for {cluster.name}: {e}")
        result["error_message"] += f"Nodes: {str(e)[:100]}. "

    # --- Pods ---
    try:
        if namespace_filter:
            all_pods = []
            for ns in namespace_filter:
                try:
                    pods = core_api.list_namespaced_pod(ns)
                    all_pods.extend(pods.items)
                except Exception:
                    pass
        else:
            pods = core_api.list_pod_for_all_namespaces()
            all_pods = pods.items

        result["total_pods"] = len(all_pods)
        pods_data = []

        for pod in all_pods:
            phase = pod.status.phase or "Unknown"
            restarts = 0
            if pod.status.container_statuses:
                restarts = sum(cs.restart_count or 0 for cs in pod.status.container_statuses)

            # Detect CrashLoopBackOff
            crash_loop = False
            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    if cs.state and cs.state.waiting and cs.state.waiting.reason == "CrashLoopBackOff":
                        crash_loop = True

            if phase == "Running":
                result["running_pods"] += 1
            elif phase == "Failed":
                result["failed_pods"] += 1
            elif phase == "Pending":
                result["pending_pods"] += 1

            pod_info = {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": phase,
                "restarts": restarts,
                "crash_loop": crash_loop,
                "node": pod.spec.node_name or "",
                "created": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else "",
            }
            pods_data.append(pod_info)

        result["pods_data"] = pods_data

    except Exception as e:
        logger.error(f"Pod collection failed for {cluster.name}: {e}")
        result["error_message"] += f"Pods: {str(e)[:100]}. "

    # --- Events (warnings only, last 1 hour) ---
    try:
        if namespace_filter:
            all_events = []
            for ns in namespace_filter:
                try:
                    events = core_api.list_namespaced_event(ns)
                    all_events.extend(events.items)
                except Exception:
                    pass
        else:
            events = core_api.list_event_for_all_namespaces()
            all_events = events.items

        events_data = []
        for ev in all_events:
            if ev.type != "Warning":
                continue
            events_data.append({
                "type": ev.type,
                "reason": ev.reason,
                "message": (ev.message or "")[:200],
                "count": ev.count or 1,
                "namespace": ev.metadata.namespace,
                "object": f"{ev.involved_object.kind}/{ev.involved_object.name}" if ev.involved_object else "",
                "last_seen": ev.last_timestamp.isoformat() if ev.last_timestamp else "",
            })

        # Sort by count descending, limit to 50
        events_data.sort(key=lambda x: x["count"], reverse=True)
        result["events_data"] = events_data[:50]

    except Exception as e:
        logger.error(f"Event collection failed for {cluster.name}: {e}")
        result["error_message"] += f"Events: {str(e)[:100]}. "

    # --- Metrics (from metrics-server if available) ---
    try:
        from kubernetes.client import CustomObjectsApi
        custom_api = CustomObjectsApi()

        # Node metrics
        node_metrics = custom_api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")
        total_cpu_used = 0
        total_mem_used = 0
        for nm in node_metrics.get("items", []):
            cpu = _parse_cpu(nm.get("usage", {}).get("cpu", "0"))
            mem = _parse_memory(nm.get("usage", {}).get("memory", "0"))
            total_cpu_used += cpu
            total_mem_used += mem

            # Update node data with usage
            for nd in result["nodes_data"]:
                if nd["name"] == nm["metadata"]["name"]:
                    nd["cpu_used"] = round(cpu, 2)
                    nd["memory_used_gb"] = round(mem, 2)
                    nd["cpu_pct"] = round(cpu / max(nd["cpu_capacity"], 0.01) * 100, 1)
                    nd["memory_pct"] = round(mem / max(nd["memory_capacity_gb"], 0.01) * 100, 1)

        result["cpu_used_cores"] = round(total_cpu_used, 2)
        result["memory_used_gb"] = round(total_mem_used, 2)

        # Pod metrics
        if namespace_filter:
            for ns in namespace_filter:
                try:
                    pod_metrics = custom_api.list_namespaced_custom_object("metrics.k8s.io", "v1beta1", ns, "pods")
                    _update_pod_metrics(result["pods_data"], pod_metrics.get("items", []))
                except Exception:
                    pass
        else:
            pod_metrics = custom_api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "pods")
            _update_pod_metrics(result["pods_data"], pod_metrics.get("items", []))

    except Exception as e:
        logger.debug(f"Metrics-server not available for {cluster.name}: {e}")
        # Metrics-server is optional — not an error

    # Determine overall status
    if result["error_message"]:
        result["cluster_status"] = "degraded"
    if result["ready_nodes"] == 0 and result["total_nodes"] > 0:
        result["cluster_status"] = "critical"
    if result["failed_pods"] > 0 or any(p["crash_loop"] for p in result["pods_data"]):
        if result["cluster_status"] == "healthy":
            result["cluster_status"] = "degraded"

    return result


def _update_pod_metrics(pods_data, metrics_items):
    for pm in metrics_items:
        pod_name = pm["metadata"]["name"]
        containers = pm.get("containers", [])
        total_cpu = sum(_parse_cpu(c.get("usage", {}).get("cpu", "0")) for c in containers)
        total_mem = sum(_parse_memory(c.get("usage", {}).get("memory", "0")) for c in containers)
        for pd in pods_data:
            if pd["name"] == pod_name:
                pd["cpu_cores"] = round(total_cpu, 3)
                pd["memory_mb"] = round(total_mem * 1024, 1)


def _parse_cpu(val: str) -> float:
    """Parse K8s CPU value to cores. E.g., '500m' → 0.5, '2' → 2.0"""
    val = str(val).strip()
    if val.endswith("n"):
        return float(val[:-1]) / 1_000_000_000
    if val.endswith("m"):
        return float(val[:-1]) / 1000
    return float(val)


def _parse_memory(val: str) -> float:
    """Parse K8s memory value to GB. E.g., '1Gi' → 1.0, '512Mi' → 0.5"""
    val = str(val).strip()
    if val.endswith("Ki"):
        return float(val[:-2]) / 1_048_576
    if val.endswith("Mi"):
        return float(val[:-2]) / 1024
    if val.endswith("Gi"):
        return float(val[:-2])
    if val.endswith("Ti"):
        return float(val[:-2]) * 1024
    # Plain bytes
    try:
        return float(val) / 1_073_741_824
    except ValueError:
        return 0
