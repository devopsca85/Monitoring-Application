import logging

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from app.checks import run_login_check, run_multi_page_check, run_uptime_check
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Monitoring Engine")


class MonitorJob(BaseModel):
    site_id: int
    site_url: str
    site_name: str
    check_type: str  # uptime, login, multi_page
    credentials: dict | None = None
    pages: list[dict] = []


@app.post("/run-check")
async def run_check(job: MonitorJob):
    """Execute a monitoring check and report results back to the API."""
    logger.info(f"Running {job.check_type} check for {job.site_name} ({job.site_url})")

    site = {"url": job.site_url, "name": job.site_name}

    if job.check_type == "uptime":
        result = await run_uptime_check(site)
    elif job.check_type == "login":
        result = await run_login_check(site, job.credentials or {})
    elif job.check_type == "multi_page":
        result = await run_multi_page_check(site, job.credentials or {}, job.pages)
    else:
        result = {
            "status": "critical",
            "response_time_ms": 0,
            "status_code": 0,
            "error_message": f"Unknown check type: {job.check_type}",
        }

    # Submit results to backend API
    payload = {
        "site_id": job.site_id,
        "check_type": job.check_type,
        "status": result["status"],
        "response_time_ms": result["response_time_ms"],
        "status_code": result.get("status_code", 0),
        "error_message": result.get("error_message", ""),
        "screenshot_url": result.get("screenshot_url", ""),
        "details": result.get("details", ""),
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.BACKEND_API_URL}/monitoring/results",
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            logger.info(f"Result submitted for site {job.site_id}: {result['status']}")
    except Exception as e:
        logger.error(f"Failed to submit result for site {job.site_id}: {e}")

    return {"status": "completed", "result": result}


@app.get("/health")
def health():
    return {"status": "healthy", "engine": "playwright"}
