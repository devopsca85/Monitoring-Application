from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import encrypt_credential
from app.models.models import Site, SiteCredential, SitePage, User
from app.models.schemas import SiteCreate, SiteCredentialResponse, SiteUpdate
from app.routes.auth import get_current_user

router = APIRouter(prefix="/sites", tags=["sites"])


def _safe_enum(val, default=""):
    if val is None:
        return default
    return val.value if hasattr(val, 'value') else str(val)


def _serialize_site(s):
    """Safely serialize a Site ORM object to a dict — handles missing columns gracefully."""
    try:
        tech = _safe_enum(s.tech_stack, "other")
    except Exception:
        tech = "other"

    try:
        slow = s.slow_threshold_ms or 10000
    except Exception:
        slow = 10000

    try:
        pages = [
            {
                "id": p.id, "page_url": p.page_url, "page_name": p.page_name,
                "expected_element": p.expected_element, "expected_text": p.expected_text,
                "sort_order": p.sort_order or 0,
            }
            for p in (s.pages or [])
        ]
    except Exception:
        pages = []

    return {
        "id": s.id,
        "name": s.name,
        "url": s.url,
        "check_type": _safe_enum(s.check_type, "uptime"),
        "tech_stack": tech,
        "check_interval_minutes": s.check_interval_minutes or 5,
        "slow_threshold_ms": slow,
        "is_active": bool(s.is_active) if s.is_active is not None else True,
        "notification_channel": _safe_enum(s.notification_channel, "email"),
        "notification_emails": s.notification_emails or "",
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "pages": pages,
    }


@router.get("/debug")
def debug_sites(db: Session = Depends(get_db)):
    """Debug: raw site data without auth or serialization."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        sites = db.query(Site).all()
        logger.info(f"DEBUG: found {len(sites)} sites")
        return [{"id": s.id, "name": s.name, "url": s.url} for s in sites]
    except Exception as e:
        logger.error(f"DEBUG sites failed: {e}", exc_info=True)
        return {"error": str(e)}


@router.get("/")
def list_sites(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    import logging
    logger = logging.getLogger(__name__)
    try:
        sites = db.query(Site).all()
        logger.info(f"list_sites: found {len(sites)} sites")
        result = []
        for s in sites:
            try:
                result.append(_serialize_site(s))
            except Exception as e:
                logger.error(f"Failed to serialize site {s.id} ({s.name}): {e}", exc_info=True)
                result.append({"id": s.id, "name": s.name, "url": s.url, "error": str(e)})
        return result
    except Exception as e:
        logger.error(f"list_sites failed: {e}", exc_info=True)
        return []


@router.get("/{site_id}")
def get_site(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = db.query(Site).filter(Site.id == site_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Site not found")
    return _serialize_site(s)


@router.post("/", status_code=201)
async def create_site(
    site_in: SiteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    site = Site(
        name=site_in.name,
        url=site_in.url,
        check_type=site_in.check_type,
        tech_stack=site_in.tech_stack or "other",
        check_interval_minutes=site_in.check_interval_minutes,
        slow_threshold_ms=site_in.slow_threshold_ms,
        notification_channel=site_in.notification_channel,
        notification_emails=site_in.notification_emails,
    )
    db.add(site)
    db.flush()

    if site_in.credentials:
        cred = site_in.credentials
        db_cred = SiteCredential(
            site_id=site.id,
            login_url=cred.login_url,
            username_selector=cred.username_selector,
            password_selector=cred.password_selector,
            submit_selector=cred.submit_selector,
            success_indicator=cred.success_indicator,
            expected_page=cred.expected_page or "mainpage.aspx",
            encrypted_username=encrypt_credential(cred.username),
            encrypted_password=encrypt_credential(cred.password),
        )
        db.add(db_cred)

    for page in site_in.pages:
        db_page = SitePage(
            site_id=site.id,
            page_url=page.page_url,
            page_name=page.page_name,
            expected_element=page.expected_element,
            expected_text=page.expected_text,
            sort_order=page.sort_order,
        )
        db.add(db_page)

    db.commit()
    db.refresh(site)

    # Notify admins about new site
    from app.services.notification_service import send_admin_notification
    await send_admin_notification(
        subject=f"[NEW SITE] {site.name} added to monitoring",
        message=(
            f"<strong>{site.name}</strong> ({site.url}) has been added "
            f"to monitoring by <strong>{user.email}</strong>.<br/>"
            f"Check type: <strong>{site.check_type.value}</strong> | "
            f"Interval: <strong>{site.check_interval_minutes} min</strong>"
        ),
    )

    return _serialize_site(site)


@router.get("/{site_id}/credentials", response_model=SiteCredentialResponse | None)
def get_site_credentials(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cred = db.query(SiteCredential).filter(SiteCredential.site_id == site_id).first()
    return cred


@router.put("/{site_id}", )
def update_site(
    site_id: int,
    site_in: SiteUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    update_data = site_in.model_dump(exclude_unset=True, exclude={"credentials", "pages"})
    for field, value in update_data.items():
        setattr(site, field, value)

    # Update credentials
    if site_in.credentials is not None:
        cred = site_in.credentials
        existing_cred = db.query(SiteCredential).filter(SiteCredential.site_id == site.id).first()
        if existing_cred:
            existing_cred.login_url = cred.login_url
            existing_cred.username_selector = cred.username_selector
            existing_cred.password_selector = cred.password_selector
            existing_cred.submit_selector = cred.submit_selector
            existing_cred.success_indicator = cred.success_indicator
            existing_cred.expected_page = cred.expected_page or "mainpage.aspx"
            if cred.username:
                existing_cred.encrypted_username = encrypt_credential(cred.username)
            if cred.password:
                existing_cred.encrypted_password = encrypt_credential(cred.password)
        else:
            db_cred = SiteCredential(
                site_id=site.id,
                login_url=cred.login_url,
                username_selector=cred.username_selector,
                password_selector=cred.password_selector,
                submit_selector=cred.submit_selector,
                success_indicator=cred.success_indicator,
                expected_page=cred.expected_page or "mainpage.aspx",
                encrypted_username=encrypt_credential(cred.username),
                encrypted_password=encrypt_credential(cred.password),
            )
            db.add(db_cred)

    # Update pages
    if site_in.pages is not None:
        db.query(SitePage).filter(SitePage.site_id == site.id).delete()
        for page in site_in.pages:
            db_page = SitePage(
                site_id=site.id,
                page_url=page.page_url,
                page_name=page.page_name,
                expected_element=page.expected_element,
                expected_text=page.expected_text,
                sort_order=page.sort_order,
            )
            db.add(db_page)

    db.commit()
    db.refresh(site)
    return _serialize_site(site)


@router.delete("/{site_id}", status_code=204)
async def delete_site(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    site_name = site.name
    site_url = site.url
    deleted_by = user.email

    db.delete(site)
    db.commit()

    # Notify admins about site removal
    from app.services.notification_service import send_admin_notification
    await send_admin_notification(
        subject=f"[REMOVED] Site Deleted: {site_name}",
        message=(
            f"<strong>{site_name}</strong> ({site_url}) has been removed "
            f"from monitoring by <strong>{deleted_by}</strong>."
        ),
    )
