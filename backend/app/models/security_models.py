"""
Security & Compliance Models
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SecurityScan(Base):
    """Results from a DAST-style security scan of a site."""
    __tablename__ = "security_scans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    scanned_at = Column(DateTime, server_default=func.now(), index=True)
    score = Column(Integer, default=0)  # 0-100 security score
    grade = Column(String(5))  # A+, A, B, C, D, F
    total_findings = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)
    findings = Column(JSON)  # [{category, severity, title, description, recommendation}]
    headers_data = Column(JSON)  # Raw response headers
    ssl_data = Column(JSON)  # SSL certificate details
    error_message = Column(Text)

    site = relationship("Site")


class ComplianceFramework(Base):
    """Compliance framework (SOC 2, GDPR, etc.)"""
    __tablename__ = "compliance_frameworks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)  # SOC 2, GDPR, HIPAA, PCI-DSS
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    controls = relationship("ComplianceControl", back_populates="framework", cascade="all, delete-orphan")


class ComplianceControl(Base):
    """Individual control within a framework."""
    __tablename__ = "compliance_controls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    framework_id = Column(Integer, ForeignKey("compliance_frameworks.id", ondelete="CASCADE"))
    control_id = Column(String(50))  # e.g., CC6.1, Art.32
    category = Column(String(255))  # e.g., Logical Access, Data Protection
    title = Column(String(500), nullable=False)
    description = Column(Text)
    check_type = Column(String(50), default="manual")  # manual, automated
    status = Column(String(50), default="not_started")  # not_started, in_progress, compliant, non_compliant, not_applicable
    evidence = Column(Text)  # Notes or evidence description
    assigned_to = Column(String(255))
    due_date = Column(DateTime)
    last_reviewed = Column(DateTime)
    reviewed_by = Column(String(255))

    framework = relationship("ComplianceFramework", back_populates="controls")
