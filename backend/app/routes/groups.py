"""
Site Groups API — CRUD for groups with shared credentials.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import encrypt_credential, decrypt_credential
from app.models.models import SiteGroup, User
from app.routes.auth import get_current_user

router = APIRouter(prefix="/groups", tags=["groups"])


class GroupCreate(BaseModel):
    name: str
    description: str = ""
    environment: str = ""
    login_url: str = ""
    username_selector: str = "#username"
    password_selector: str = "#password"
    submit_selector: str = "input[type='submit']"
    success_indicator: str = ""
    expected_page: str = "mainpage.aspx"
    username: str = ""
    password: str = ""


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    environment: str | None = None
    login_url: str | None = None
    username_selector: str | None = None
    password_selector: str | None = None
    submit_selector: str | None = None
    success_indicator: str | None = None
    expected_page: str | None = None
    username: str | None = None
    password: str | None = None


def _serialize_group(g, include_credentials=False):
    data = {
        "id": g.id,
        "name": g.name,
        "description": g.description or "",
        "environment": g.environment or "",
        "login_url": g.login_url or "",
        "username_selector": g.username_selector or "#username",
        "password_selector": g.password_selector or "#password",
        "submit_selector": g.submit_selector or "input[type='submit']",
        "success_indicator": g.success_indicator or "",
        "expected_page": g.expected_page or "mainpage.aspx",
        "has_credentials": bool(g.encrypted_username and g.encrypted_password),
        "site_count": len(g.sites) if g.sites else 0,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }
    return data


@router.get("/")
def list_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    groups = db.query(SiteGroup).order_by(SiteGroup.name).all()
    return [_serialize_group(g) for g in groups]


@router.get("/{group_id}")
def get_group(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = db.query(SiteGroup).filter(SiteGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    result = _serialize_group(g)
    # Include site list
    from app.routes.sites import _serialize_site
    result["sites"] = [_serialize_site(s) for s in (g.sites or [])]
    return result


@router.get("/{group_id}/credentials")
def get_group_credentials(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return group credential config (without actual username/password)."""
    g = db.query(SiteGroup).filter(SiteGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    return {
        "login_url": g.login_url or "",
        "username_selector": g.username_selector or "#username",
        "password_selector": g.password_selector or "#password",
        "submit_selector": g.submit_selector or "input[type='submit']",
        "success_indicator": g.success_indicator or "",
        "expected_page": g.expected_page or "mainpage.aspx",
        "has_credentials": bool(g.encrypted_username and g.encrypted_password),
    }


@router.post("/", status_code=201)
def create_group(data: GroupCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    existing = db.query(SiteGroup).filter(SiteGroup.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Group name already exists")

    g = SiteGroup(
        name=data.name,
        description=data.description,
        environment=data.environment,
        login_url=data.login_url,
        username_selector=data.username_selector,
        password_selector=data.password_selector,
        submit_selector=data.submit_selector,
        success_indicator=data.success_indicator,
        expected_page=data.expected_page,
    )
    if data.username:
        g.encrypted_username = encrypt_credential(data.username)
    if data.password:
        g.encrypted_password = encrypt_credential(data.password)

    db.add(g)
    db.commit()
    return {"status": "Group created", "id": g.id}


@router.put("/{group_id}")
def update_group(group_id: int, data: GroupUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    g = db.query(SiteGroup).filter(SiteGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")

    for field in ["name", "description", "environment", "login_url",
                   "username_selector", "password_selector", "submit_selector",
                   "success_indicator", "expected_page"]:
        val = getattr(data, field, None)
        if val is not None:
            setattr(g, field, val)

    if data.username:
        g.encrypted_username = encrypt_credential(data.username)
    if data.password:
        g.encrypted_password = encrypt_credential(data.password)

    db.commit()
    return {"status": "Group updated"}


@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    g = db.query(SiteGroup).filter(SiteGroup.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    db.delete(g)
    db.commit()
    return {"status": "Group deleted"}
