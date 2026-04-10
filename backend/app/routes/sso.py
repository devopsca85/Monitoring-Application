import logging

import httpx
import msal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import (
    create_access_token,
    decrypt_credential,
    encrypt_credential,
    hash_password,
)
from app.models.models import SystemSetting, User
from app.models.schemas import AzureSsoCallbackRequest, Token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sso", tags=["sso"])


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


def _get_sso_config(db: Session) -> dict | None:
    enabled = _get_setting(db, "sso_enabled")
    if enabled != "true":
        return None

    tenant_id = _get_setting(db, "sso_tenant_id")
    client_id = _get_setting(db, "sso_client_id")
    client_secret = _get_setting(db, "sso_client_secret")
    redirect_uri = _get_setting(db, "sso_redirect_uri")

    if not all([tenant_id, client_id, client_secret, redirect_uri]):
        return None

    return {
        "tenant_id": tenant_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "authority": f"https://login.microsoftonline.com/{tenant_id}",
        "redirect_uri": redirect_uri,
        "admin_group_id": _get_setting(db, "sso_admin_group_id") or "",
        "user_group_id": _get_setting(db, "sso_user_group_id") or "",
    }


@router.get("/config")
def sso_config(db: Session = Depends(get_db)):
    """Public endpoint — returns SSO config for the login page (no secrets)."""
    enabled = _get_setting(db, "sso_enabled") == "true"
    if not enabled:
        return {"enabled": False}

    tenant_id = _get_setting(db, "sso_tenant_id")
    client_id = _get_setting(db, "sso_client_id")
    redirect_uri = _get_setting(db, "sso_redirect_uri")

    if not all([tenant_id, client_id, redirect_uri]):
        return {"enabled": False}

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    auth_url = (
        f"{authority}/oauth2/v2.0/authorize"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&scope=openid+profile+email+User.Read"
        f"&response_mode=query"
    )

    return {
        "enabled": True,
        "auth_url": auth_url,
        "redirect_uri": redirect_uri,
    }


@router.post("/callback", response_model=Token)
async def sso_callback(
    data: AzureSsoCallbackRequest,
    db: Session = Depends(get_db),
):
    """Exchange authorization code for tokens and create/login user."""
    config = _get_sso_config(db)
    if not config:
        raise HTTPException(status_code=400, detail="Azure SSO is not configured")

    # Always use the redirect_uri from settings — must match what Azure has registered
    redirect_uri = config["redirect_uri"]

    try:
        app = msal.ConfidentialClientApplication(
            config["client_id"],
            authority=config["authority"],
            client_credential=config["client_secret"],
        )
        result = app.acquire_token_by_authorization_code(
            data.code,
            scopes=["User.Read"],
            redirect_uri=redirect_uri,
        )
    except Exception as e:
        logger.error(f"MSAL token exchange failed: {e}")
        raise HTTPException(status_code=400, detail=f"SSO authentication failed: {str(e)}")

    if "error" in result:
        logger.error(f"SSO token error: {result.get('error_description', result.get('error'))}")
        raise HTTPException(
            status_code=400,
            detail=result.get("error_description", "SSO authentication failed"),
        )

    id_token_claims = result.get("id_token_claims", {})
    email = (
        id_token_claims.get("preferred_username")
        or id_token_claims.get("email")
        or id_token_claims.get("upn")
    )
    full_name = id_token_claims.get("name", "")

    if not email:
        raise HTTPException(status_code=400, detail="Could not get email from Azure AD")

    logger.info(f"SSO login: {email} ({full_name})")

    # Check group membership
    is_admin = False
    access_token = result.get("access_token")
    admin_group_id = config.get("admin_group_id", "")
    user_group_id = config.get("user_group_id", "")

    if access_token and (admin_group_id or user_group_id):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://graph.microsoft.com/v1.0/me/memberOf",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    groups = resp.json().get("value", [])
                    group_ids = {g.get("id", "") for g in groups}

                    if admin_group_id and admin_group_id in group_ids:
                        is_admin = True
                    elif user_group_id and user_group_id not in group_ids:
                        raise HTTPException(
                            status_code=403,
                            detail="You are not in an authorized group",
                        )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Failed to check group membership: {e}")

    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=hash_password(f"sso-{email}-{id_token_claims.get('oid', '')}"),
            full_name=full_name,
            is_admin=is_admin,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"SSO: Created new user {email} (admin={is_admin})")
    else:
        user.full_name = full_name or user.full_name
        if admin_group_id:
            user.is_admin = is_admin
        db.commit()

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Your account is disabled")

    token = create_access_token(data={"sub": user.email})
    return {"access_token": token}
