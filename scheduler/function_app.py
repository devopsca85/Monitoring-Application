import json
import logging
import os

import azure.functions as func
import httpx

app = func.FunctionApp()

BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8000/api/v1")
MONITORING_ENGINE_URL = os.environ.get("MONITORING_ENGINE_URL", "http://localhost:8001")


@app.timer_trigger(
    schedule="0 */5 * * * *",  # Every 5 minutes
    arg_name="timer",
    run_on_startup=False,
)
def monitor_trigger(timer: func.TimerRequest) -> None:
    logging.info("Monitor trigger fired")

    if timer.past_due:
        logging.warning("Timer is past due")

    try:
        # Fetch active sites from backend
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{BACKEND_API_URL}/sites/",
                headers={"Authorization": f"Bearer {os.environ.get('SERVICE_TOKEN', '')}"},
            )
            resp.raise_for_status()
            sites = resp.json()

        logging.info(f"Found {len(sites)} sites to check")

        # Trigger monitoring for each active site
        with httpx.Client(timeout=60) as client:
            for site in sites:
                if not site.get("is_active", False):
                    continue

                job = {
                    "site_id": site["id"],
                    "site_url": site["url"],
                    "site_name": site["name"],
                    "check_type": site["check_type"],
                    "credentials": None,
                    "pages": site.get("pages", []),
                }

                # For login/multi_page, we need credentials from the backend
                # The monitoring engine handles decryption via the backend API

                try:
                    resp = client.post(
                        f"{MONITORING_ENGINE_URL}/run-check",
                        json=job,
                        timeout=60,
                    )
                    resp.raise_for_status()
                    logging.info(
                        f"Check triggered for {site['name']}: {resp.json()}"
                    )
                except Exception as e:
                    logging.error(
                        f"Failed to trigger check for {site['name']}: {e}"
                    )

    except Exception as e:
        logging.error(f"Monitor trigger failed: {e}")
