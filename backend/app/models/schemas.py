from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.models import CheckType, AlertStatus, NotificationChannel


# --- Auth ---
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    is_active: bool
    is_admin: bool
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


class SiteUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    check_type: CheckType | None = None
    check_interval_minutes: int | None = None
    is_active: bool | None = None
    notification_channel: NotificationChannel | None = None
    notification_emails: str | None = None


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
