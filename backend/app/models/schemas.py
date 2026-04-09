from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.models import CheckType, AlertStatus, NotificationChannel


# --- Auth ---
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str | None = None


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    current_password: str | None = None
    new_password: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    is_active: bool
    is_admin: bool
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Site ---
class SiteCredentialCreate(BaseModel):
    login_url: str
    username_selector: str = "#username"
    password_selector: str = "#password"
    submit_selector: str = "button[type='submit']"
    success_indicator: str = ""
    expected_page: str = "mainpage.aspx"
    username: str
    password: str


class SitePageCreate(BaseModel):
    page_url: str
    page_name: str = ""
    expected_element: str = ""
    expected_text: str = ""
    sort_order: int = 0


class SiteCreate(BaseModel):
    name: str
    url: str
    check_type: CheckType = CheckType.UPTIME
    check_interval_minutes: int = 5
    notification_channel: NotificationChannel = NotificationChannel.EMAIL
    notification_emails: str = ""
    credentials: SiteCredentialCreate | None = None
    pages: list[SitePageCreate] = []


class SiteCredentialResponse(BaseModel):
    id: int
    login_url: str | None
    username_selector: str | None
    password_selector: str | None
    submit_selector: str | None
    success_indicator: str | None
    expected_page: str | None
    model_config = {"from_attributes": True}


class SiteUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    check_type: CheckType | None = None
    check_interval_minutes: int | None = None
    is_active: bool | None = None
    notification_channel: NotificationChannel | None = None
    notification_emails: str | None = None
    credentials: SiteCredentialCreate | None = None
    pages: list[SitePageCreate] | None = None


class SitePageResponse(BaseModel):
    id: int
    page_url: str
    page_name: str | None
    expected_element: str | None
    expected_text: str | None
    sort_order: int
    model_config = {"from_attributes": True}


class SiteResponse(BaseModel):
    id: int
    name: str
    url: str
    check_type: CheckType
    check_interval_minutes: int
    is_active: bool
    notification_channel: NotificationChannel
    notification_emails: str | None
    created_at: datetime | None
    pages: list[SitePageResponse] = []
    model_config = {"from_attributes": True}


# --- Monitoring Result ---
class MonitoringResultCreate(BaseModel):
    site_id: int
    check_type: CheckType
    status: AlertStatus
    response_time_ms: float = 0
    status_code: int = 0
    error_message: str = ""
    screenshot_url: str = ""
    details: str = ""


class MonitoringResultResponse(BaseModel):
    id: int
    site_id: int
    check_type: CheckType
    status: AlertStatus
    response_time_ms: float | None
    status_code: int | None
    error_message: str | None
    screenshot_url: str | None
    details: str | None
    checked_at: datetime | None
    model_config = {"from_attributes": True}


# --- Alert ---
class AlertResponse(BaseModel):
    id: int
    site_id: int
    alert_type: AlertStatus
    message: str | None
    notified: bool
    resolved: bool
    created_at: datetime | None
    resolved_at: datetime | None
    model_config = {"from_attributes": True}


# --- Dashboard ---
class DashboardStats(BaseModel):
    total_sites: int
    sites_up: int
    sites_down: int
    sites_warning: int
    avg_response_time: float


# --- Admin: User Management ---
class AdminUserCreate(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    is_admin: bool = False
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    full_name: str | None = None
    is_admin: bool | None = None
    is_active: bool | None = None


# --- Admin: System Settings ---
class SystemSettingValue(BaseModel):
    key: str
    value: str


class SystemSettingsResponse(BaseModel):
    smtp_host: str = ""
    smtp_port: str = "587"
    smtp_user: str = ""
    smtp_password_set: bool = False
    smtp_from_email: str = ""
    smtp_use_tls: str = "true"
    teams_webhook_url: str = ""
    teams_webhook_set: bool = False

class SmtpSettingsUpdate(BaseModel):
    smtp_host: str = ""
    smtp_port: str = "587"
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: str = "true"

class TeamsSettingsUpdate(BaseModel):
    teams_webhook_url: str = ""

class SmtpTestRequest(BaseModel):
    to_email: str
