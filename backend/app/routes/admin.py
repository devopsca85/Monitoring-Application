from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import encrypt_credential, decrypt_credential, hash_password
from app.models.models import SystemSetting, User
from app.models.schemas import (
    AdminUserCreate,
    AdminUserUpdate,
    AzureSsoSettings,
    AzureSsoSettingsResponse,
    SmtpSettingsUpdate,
    SmtpTestRequest,
    SystemSettingsResponse,
    TeamsSettingsUpdate,
    UserResponse,
)
from app.routes.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ---------------------------------------------------------------------------
# Helper: read / write system settings
# ---------------------------------------------------------------------------
def _get_setting(db: Session, key: str) -> str:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not row:
        return ""
    if row.is_encrypted and row.value:
        try:
            return decrypt_credential(row.value)
        except Exception:
            return ""
    return row.value


def _set_setting(db: Session, key: str, value: str, encrypted: bool = False) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    store_value = encrypt_credential(value) if encrypted and value else value
    if row:
        row.value = store_value
        row.is_encrypted = encrypted
    else:
        db.add(SystemSetting(key=key, value=store_value, is_encrypted=encrypted))


# ===========================================================================
# USER MANAGEMENT
# ===========================================================================
@router.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(User).order_by(User.id).all()


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    user_in: AdminUserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        is_admin=user_in.is_admin,
        is_active=user_in.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_in.email is not None:
        existing = db.query(User).filter(User.email == user_in.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = user_in.email

    if user_in.password is not None and user_in.password:
        user.hashed_password = hash_password(user_in.password)

    if user_in.full_name is not None:
        user.full_name = user_in.full_name

    if user_in.is_admin is not None:
        # Prevent removing your own admin status
        if user.id == admin.id and not user_in.is_admin:
            raise HTTPException(status_code=400, detail="Cannot remove your own admin status")
        user.is_admin = user_in.is_admin

    if user_in.is_active is not None:
        if user.id == admin.id and not user_in.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
        user.is_active = user_in.is_active

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    db.delete(user)
    db.commit()


# ===========================================================================
# SYSTEM SETTINGS — SMTP
# ===========================================================================
@router.get("/settings", response_model=SystemSettingsResponse)
def get_settings(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    smtp_password = _get_setting(db, "smtp_password")
    teams_webhook = _get_setting(db, "teams_webhook_url")
    return SystemSettingsResponse(
        smtp_host=_get_setting(db, "smtp_host"),
        smtp_port=_get_setting(db, "smtp_port") or "587",
        smtp_user=_get_setting(db, "smtp_user"),
        smtp_password_set=bool(smtp_password),
        smtp_from_email=_get_setting(db, "smtp_from_email"),
        smtp_use_tls=_get_setting(db, "smtp_use_tls") or "true",
        teams_webhook_url=teams_webhook[:8] + "****" if teams_webhook else "",
        teams_webhook_set=bool(teams_webhook),
        teams_enabled=_get_setting(db, "teams_enabled") != "false",
    )


@router.put("/settings/smtp")
def update_smtp_settings(
    data: SmtpSettingsUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    _set_setting(db, "smtp_host", data.smtp_host)
    _set_setting(db, "smtp_port", data.smtp_port)
    _set_setting(db, "smtp_user", data.smtp_user)
    if data.smtp_password:
        _set_setting(db, "smtp_password", data.smtp_password, encrypted=True)
    _set_setting(db, "smtp_from_email", data.smtp_from_email)
    _set_setting(db, "smtp_use_tls", data.smtp_use_tls)
    db.commit()
    return {"status": "SMTP settings saved"}


@router.put("/settings/teams")
def update_teams_settings(
    data: TeamsSettingsUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if data.teams_webhook_url:
        _set_setting(db, "teams_webhook_url", data.teams_webhook_url, encrypted=True)
    if data.teams_enabled is not None:
        _set_setting(db, "teams_enabled", "true" if data.teams_enabled else "false")
    db.commit()
    return {"status": "Teams settings saved"}


@router.post("/settings/teams/test")
async def test_teams(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Send a test message to the configured Teams webhook."""
    webhook_url = _get_setting(db, "teams_webhook_url")
    if not webhook_url:
        raise HTTPException(status_code=400, detail="Teams webhook URL not configured")

    import httpx
    card = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "007AFF",
        "summary": "Test — Monitoring Application",
        "sections": [
            {
                "activityTitle": "Test — Monitoring Application",
                "text": "This is a test notification. Your Teams webhook is configured correctly.",
                "markdown": True,
            }
        ],
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                webhook_url,
                json=card,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
        return {"status": "Test message sent to Teams"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Teams test failed: {str(e)}")


@router.post("/settings/smtp/test")
async def test_smtp(
    data: SmtpTestRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Send a test email using the stored SMTP settings."""
    import smtplib
    from email.mime.text import MIMEText

    host = _get_setting(db, "smtp_host")
    port = int(_get_setting(db, "smtp_port") or "587")
    user = _get_setting(db, "smtp_user")
    password = _get_setting(db, "smtp_password")
    from_email = _get_setting(db, "smtp_from_email") or user
    use_tls = _get_setting(db, "smtp_use_tls") != "false"

    if not host:
        raise HTTPException(status_code=400, detail="SMTP host not configured")

    msg = MIMEText(
        "<h2>Monitoring Alert System</h2><p>This is a test email from your monitoring application. SMTP is configured correctly.</p>",
        "html",
    )
    msg["Subject"] = "Test Email — Monitoring Application"
    msg["From"] = from_email
    msg["To"] = data.to_email

    try:
        if use_tls:
            server = smtplib.SMTP(host, port, timeout=15)
            server.starttls()
        else:
            server = smtplib.SMTP(host, port, timeout=15)
        if user and password:
            server.login(user, password)
        server.sendmail(from_email, [data.to_email], msg.as_string())
        server.quit()
        return {"status": "Test email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SMTP test failed: {str(e)}")


# ===========================================================================
# AZURE SSO SETTINGS
# ===========================================================================
@router.get("/settings/sso", response_model=AzureSsoSettingsResponse)
def get_sso_settings(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    client_secret = _get_setting(db, "sso_client_secret")
    return AzureSsoSettingsResponse(
        enabled=_get_setting(db, "sso_enabled") == "true",
        tenant_id=_get_setting(db, "sso_tenant_id"),
        client_id=_get_setting(db, "sso_client_id"),
        client_secret_set=bool(client_secret),
        redirect_uri=_get_setting(db, "sso_redirect_uri"),
        admin_group_id=_get_setting(db, "sso_admin_group_id"),
        user_group_id=_get_setting(db, "sso_user_group_id"),
    )


@router.put("/settings/sso")
def update_sso_settings(
    data: AzureSsoSettings,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    _set_setting(db, "sso_enabled", "true" if data.enabled else "false")
    _set_setting(db, "sso_tenant_id", data.tenant_id)
    _set_setting(db, "sso_client_id", data.client_id)
    if data.client_secret:
        _set_setting(db, "sso_client_secret", data.client_secret, encrypted=True)
    _set_setting(db, "sso_redirect_uri", data.redirect_uri)
    _set_setting(db, "sso_admin_group_id", data.admin_group_id)
    _set_setting(db, "sso_user_group_id", data.user_group_id)
    db.commit()
    return {"status": "Azure SSO settings saved"}
