import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CheckType(str, enum.Enum):
    UPTIME = "uptime"
    LOGIN = "login"
    MULTI_PAGE = "multi_page"


class AlertStatus(str, enum.Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    TEAMS = "teams"
    BOTH = "both"


class TechStack(str, enum.Enum):
    ASP_NET = "asp_net"
    ASP_NET_CORE = "asp_net_core"
    PHP = "php"
    NODEJS = "nodejs"
    REACT = "react"
    ANGULAR = "angular"
    VUE = "vue"
    PYTHON = "python"
    JAVA = "java"
    RUBY = "ruby"
    WORDPRESS = "wordpress"
    DRUPAL = "drupal"
    STATIC = "static"
    OTHER = "other"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    check_type = Column(Enum(CheckType), default=CheckType.UPTIME)
    tech_stack = Column(String(50), default="other")
    check_interval_minutes = Column(Integer, default=5)
    slow_threshold_ms = Column(Integer, default=10000)
    is_active = Column(Boolean, default=True)
    notification_channel = Column(
        Enum(NotificationChannel), default=NotificationChannel.EMAIL
    )
    notification_emails = Column(Text)  # comma-separated
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    credentials = relationship("SiteCredential", back_populates="site", uselist=False)
    pages = relationship("SitePage", back_populates="site")
    results = relationship("MonitoringResult", back_populates="site")
    alerts = relationship("Alert", back_populates="site")


class SiteCredential(Base):
    __tablename__ = "site_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), unique=True)
    login_url = Column(String(500))
    username_selector = Column(String(255))
    password_selector = Column(String(255))
    submit_selector = Column(String(255))
    success_indicator = Column(String(255))  # CSS selector or text to verify login
    expected_page = Column(String(255), default="mainpage.aspx")  # URL fragment expected after login
    encrypted_username = Column(Text)
    encrypted_password = Column(Text)

    site = relationship("Site", back_populates="credentials")


class SitePage(Base):
    __tablename__ = "site_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"))
    page_url = Column(String(500), nullable=False)
    page_name = Column(String(255))
    expected_element = Column(String(255))  # CSS selector that must exist
    expected_text = Column(String(500))  # text that must be present
    sort_order = Column(Integer, default=0)

    site = relationship("Site", back_populates="pages")


class MonitoringResult(Base):
    __tablename__ = "monitoring_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    check_type = Column(Enum(CheckType))
    status = Column(Enum(AlertStatus))
    response_time_ms = Column(Float)
    status_code = Column(Integer)
    error_message = Column(Text)
    screenshot_url = Column(String(500))
    details = Column(Text)  # JSON string with page-by-page results
    checked_at = Column(DateTime, server_default=func.now(), index=True)

    site = relationship("Site", back_populates="results")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False, default="")
    is_encrypted = Column(Boolean, default=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    alert_type = Column(Enum(AlertStatus))
    message = Column(Text)
    notified = Column(Boolean, default=False)
    notified_at = Column(DateTime)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    false_positive = Column(Boolean, default=False)
    false_positive_by = Column(String(255))
    false_positive_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    site = relationship("Site", back_populates="alerts")


class FalsePositiveRule(Base):
    """Suppresses notifications for specific alert patterns marked as false positives."""
    __tablename__ = "false_positive_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    error_pattern = Column(String(500), nullable=False)  # substring to match in error_message
    created_by = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    site = relationship("Site")
