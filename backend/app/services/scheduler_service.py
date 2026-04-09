import asyncio
import logging

import httpx

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import decrypt_credential
from app.models.models import Site, SiteCredential, SitePage

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler_task = None


def _build_job(site: Site, db) -> dict:
    """Build a monitoring job payload for the engine, including decrypted credentials."""
    job = {
        "site_id": site.id,
        "site_url": site.url,
        "site_name": site.name,
        "check_type": site.check_type.value,
        "credentials": None,
        "pages": [],
    }

    if site.check_type.value in ("login", "multi_page"):
        cred = db.query(SiteCredential).filter(SiteCredential.site_id == site.id).first()
        if cred:
            job["credentials"] = {
                "login_url": cred.login_url,
                "username_selector": cred.username_selector,
                "password_selector": cred.password_selector,
                "submit_selector": cred.submit_selector,
                "success_indicator": cred.success_indicator or "",
                "username": decrypt_credential(cred.encrypted_username),
                "password": decrypt_credential(cred.encrypted_password),
            }

    if site.check_type.value in ("login", "multi_page"):
        pages = (
            db.query(SitePage)
            .filter(SitePage.site_id == site.id)
            .order_by(SitePage.sort_order)
            .all()
        )
        job["pages"] = [
            {
                "page_url": p.page_url,
                "page_name": p.page_name or "",
                "expected_element": p.expected_element or "",
                "expected_text": p.expected_text or "",
                "sort_order": p.sort_order,
            }
            for p in pages
        ]

    return job


async def trigger_check_for_site(site_id: int) -> dict:
    """Trigger a monitoring check for a single site. Returns the engine response."""
    db = SessionLocal()
    try:
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            return {"error": "Site not found"}
        if not site.is_active:
            return {"error": "Site is paused"}

        job = _build_job(site, db)
    finally:
        db.close()

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.MONITORING_ENGINE_URL}/run-check",
                json=job,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        logger.error(
            f"Cannot reach monitoring engine at {settings.MONITORING_ENGINE_URL}"
        )
        return {"error": f"Monitoring engine not reachable at {settings.MONITORING_ENGINE_URL}"}
    except Exception as e:
        logger.error(f"Failed to trigger check for site {site_id}: {e}")
        return {"error": str(e)}


async def _run_scheduler_loop():
    """Background loop that triggers checks for all active sites on their intervals."""
    logger.info("Background scheduler started")
    # Track last check time per site
    last_checked: dict[int, float] = {}

    while True:
        try:
            db = SessionLocal()
            try:
                sites = db.query(Site).filter(Site.is_active == True).all()
                site_data = [
                    (s.id, s.check_interval_minutes, s.name)
                    for s in sites
                ]
            finally:
                db.close()

            now = asyncio.get_event_loop().time()

            for site_id, interval_min, name in site_data:
                interval_sec = interval_min * 60
                last = last_checked.get(site_id, 0)

                if now - last >= interval_sec:
                    logger.info(f"Scheduler: triggering check for '{name}' (site {site_id})")
                    last_checked[site_id] = now
                    # Fire and forget — don't block the loop
                    asyncio.create_task(_safe_trigger(site_id, name))

        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")

        await asyncio.sleep(30)  # Check every 30 seconds


async def _safe_trigger(site_id: int, name: str):
    try:
        result = await trigger_check_for_site(site_id)
        logger.info(f"Scheduler: check completed for '{name}': {result.get('status', result.get('error', 'unknown'))}")
    except Exception as e:
        logger.error(f"Scheduler: check failed for '{name}': {e}")


def start_scheduler():
    """Start the background scheduler. Call from FastAPI startup."""
    global _scheduler_task
    _scheduler_task = asyncio.create_task(_run_scheduler_loop())
    logger.info("Background monitoring scheduler initialized")


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None
        logger.info("Background monitoring scheduler stopped")
