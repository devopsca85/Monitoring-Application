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
# Track running checks to prevent overlapping executions for same site
_running_checks: set[int] = set()


def _build_job(site_id: int, db) -> dict | None:
    """Build a monitoring job payload. Queries DB explicitly — no lazy loading."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return None
    if not site.is_active:
        return None

    job = {
        "site_id": site.id,
        "site_url": site.url,
        "site_name": site.name,
        "check_type": site.check_type.value,
        "credentials": None,
        "pages": [],
    }

    if site.check_type.value in ("login", "multi_page"):
        # FIX #6: Explicit query — no lazy loading / DetachedInstanceError
        cred = db.query(SiteCredential).filter(SiteCredential.site_id == site.id).first()
        if cred:
            try:
                job["credentials"] = {
                    "login_url": cred.login_url,
                    "username_selector": cred.username_selector,
                    "password_selector": cred.password_selector,
                    "submit_selector": cred.submit_selector,
                    "success_indicator": cred.success_indicator or "",
                    "expected_page": cred.expected_page or "mainpage.aspx",
                    "username": decrypt_credential(cred.encrypted_username),
                    "password": decrypt_credential(cred.encrypted_password),
                }
            except Exception as e:
                logger.error(f"Failed to decrypt credentials for site {site.name}: {e}")
                return None

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
    """Trigger a monitoring check for a single site."""
    db = SessionLocal()
    try:
        job = _build_job(site_id, db)
        if not job:
            return {"error": "Site not found or inactive"}
    except Exception as e:
        logger.error(f"Failed to build job for site {site_id}: {e}")
        return {"error": str(e)}
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
        msg = f"Monitoring engine not reachable at {settings.MONITORING_ENGINE_URL}"
        logger.error(msg)
        return {"error": msg}
    except Exception as e:
        logger.error(f"Check trigger failed for site {site_id}: {e}")
        return {"error": str(e)}


async def _run_daily_report_scheduler():
    """Runs the daily report at 9:00 AM CST every day."""
    from app.services.daily_report import send_daily_report
    from datetime import datetime, timedelta, timezone

    CST_OFFSET = timedelta(hours=-6)
    last_report_date = None

    while True:
        try:
            utc_now = datetime.now(timezone.utc)
            cst_now = utc_now + CST_OFFSET
            today = cst_now.date()

            if cst_now.hour == 9 and cst_now.minute < 2 and last_report_date != today:
                logger.info("Daily report: triggering 9 AM CST report")
                last_report_date = today
                try:
                    await send_daily_report()
                except Exception as e:
                    logger.error(f"Daily report send failed: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Daily report scheduler error: {e}")

        await asyncio.sleep(60)  # Check every minute


async def _run_scheduler_loop():
    """Background loop that triggers checks for all active sites on their intervals."""
    logger.info("Background scheduler started")
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
                    # FIX #7: Skip if check already running for this site
                    if site_id in _running_checks:
                        logger.debug(f"Scheduler: '{name}' check still running, skipping")
                        continue

                    logger.info(f"Scheduler: triggering check for '{name}' (site {site_id})")
                    # FIX #7: Update last_checked optimistically but retry on failure
                    last_checked[site_id] = now
                    asyncio.create_task(_safe_trigger(site_id, name, last_checked))

        except Exception as e:
            logger.error(f"Scheduler loop error: {e}", exc_info=True)

        await asyncio.sleep(15)


async def _safe_trigger(site_id: int, name: str, last_checked: dict):
    """Execute a check with proper tracking to prevent overlaps."""
    _running_checks.add(site_id)
    try:
        result = await trigger_check_for_site(site_id)
        status = result.get("status", result.get("error", "unknown"))
        logger.info(f"Scheduler: '{name}' completed: {status}")

        # FIX #7: On engine failure, reset last_checked to retry sooner
        if "error" in result:
            last_checked.pop(site_id, None)
            logger.warning(f"Scheduler: '{name}' failed, will retry next cycle")
    except Exception as e:
        logger.error(f"Scheduler: '{name}' exception: {e}")
        last_checked.pop(site_id, None)
    finally:
        _running_checks.discard(site_id)


_daily_report_task = None


def start_scheduler():
    """Start the background scheduler + daily report scheduler."""
    global _scheduler_task, _daily_report_task
    _scheduler_task = asyncio.create_task(_run_scheduler_loop())
    _daily_report_task = asyncio.create_task(_run_daily_report_scheduler())
    logger.info("Background monitoring scheduler + daily report scheduler initialized")


def stop_scheduler():
    """Stop all schedulers."""
    global _scheduler_task, _daily_report_task
    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None
    if _daily_report_task:
        _daily_report_task.cancel()
        _daily_report_task = None
    logger.info("All schedulers stopped")
