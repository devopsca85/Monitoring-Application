from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import encrypt_credential
from app.models.models import Site, SiteCredential, SitePage, User
from app.models.schemas import SiteCreate, SiteCredentialResponse, SiteResponse, SiteUpdate
from app.routes.auth import get_current_user

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("/", response_model=list[SiteResponse])
def list_sites(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return db.query(Site).all()


@router.get("/{site_id}", response_model=SiteResponse)
def get_site(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


@router.post("/", response_model=SiteResponse, status_code=201)
async def create_site(
    site_in: SiteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    site = Site(
        name=site_in.name,
        url=site_in.url,
        check_type=site_in.check_type,
        check_interval_minutes=site_in.check_interval_minutes,
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

    return site


@router.get("/{site_id}/credentials", response_model=SiteCredentialResponse | None)
def get_site_credentials(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cred = db.query(SiteCredential).filter(SiteCredential.site_id == site_id).first()
    return cred


@router.put("/{site_id}", response_model=SiteResponse)
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
    return site


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
