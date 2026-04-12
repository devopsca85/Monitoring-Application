"""
Kubernetes Monitoring Models
Stores cluster configs, node/pod snapshots, and metrics history.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CloudProvider(str, enum.Enum):
    AZURE = "azure"
    AWS = "aws"
    GCP = "gcp"
    ON_PREM = "on_prem"


class K8sEnvironment(str, enum.Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    QA = "qa"
    DEVELOPMENT = "development"


class K8sCluster(Base):
    __tablename__ = "k8s_clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    cloud_provider = Column(String(50), default="azure")  # azure, aws, gcp, on_prem
    environment = Column(String(50), default="production")  # production, staging, qa, dev
    region = Column(String(100))
    api_server_url = Column(String(500))
    auth_type = Column(String(50), default="kubeconfig")  # kubeconfig, token, azure_ad
    encrypted_kubeconfig = Column(Text)  # Fernet encrypted
    encrypted_token = Column(Text)  # Fernet encrypted
    namespace_filter = Column(String(500))  # comma-separated, empty = all
    is_active = Column(Boolean, default=True)
    check_interval_minutes = Column(Integer, default=3)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    snapshots = relationship("K8sSnapshot", back_populates="cluster", cascade="all, delete-orphan")
    alerts = relationship("K8sAlert", back_populates="cluster", cascade="all, delete-orphan")


class K8sSnapshot(Base):
    """Point-in-time snapshot of cluster state — one per check cycle."""
    __tablename__ = "k8s_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Integer, ForeignKey("k8s_clusters.id", ondelete="CASCADE"), index=True)
    checked_at = Column(DateTime, server_default=func.now(), index=True)

    # Cluster-level
    cluster_status = Column(String(50))  # healthy, degraded, critical
    k8s_version = Column(String(50))
    total_nodes = Column(Integer, default=0)
    ready_nodes = Column(Integer, default=0)
    total_pods = Column(Integer, default=0)
    running_pods = Column(Integer, default=0)
    failed_pods = Column(Integer, default=0)
    pending_pods = Column(Integer, default=0)

    # Resource totals
    cpu_capacity_cores = Column(Float)
    cpu_used_cores = Column(Float)
    memory_capacity_gb = Column(Float)
    memory_used_gb = Column(Float)

    # Detailed data (JSON)
    nodes_data = Column(JSON)  # [{name, status, cpu_pct, mem_pct, disk_pct, conditions}]
    pods_data = Column(JSON)   # [{name, namespace, status, restarts, cpu, mem, node}]
    events_data = Column(JSON) # [{type, reason, message, count, namespace, involved_object}]
    error_message = Column(Text)

    cluster = relationship("K8sCluster", back_populates="snapshots")


class K8sAlert(Base):
    __tablename__ = "k8s_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Integer, ForeignKey("k8s_clusters.id", ondelete="CASCADE"), index=True)
    alert_type = Column(String(50))  # node_not_ready, pod_crash, high_cpu, high_memory, etc.
    severity = Column(String(20))  # critical, warning
    resource_name = Column(String(255))  # node or pod name
    namespace = Column(String(255))
    message = Column(Text)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    cluster = relationship("K8sCluster", back_populates="alerts")
