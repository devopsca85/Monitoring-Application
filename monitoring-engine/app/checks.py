import json
import logging
import time

from playwright.async_api import async_playwright

from app.config import settings

logger = logging.getLogger(__name__)


async def run_uptime_check(site: dict) -> dict:
    """Simple HTTP/page load check."""
    start = time.time()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            response = await page.goto(
                site["url"],
                timeout=settings.BROWSER_TIMEOUT_MS,
                wait_until="domcontentloaded",
            )

            elapsed = (time.time() - start) * 1000
            status_code = response.status if response else 0

            await browser.close()

            if status_code >= 500:
                return {
                    "status": "critical",
                    "response_time_ms": elapsed,
                    "status_code": status_code,
                    "error_message": f"HTTP {status_code} Server Error",
                }

            if status_code == 404:
                return {
                    "status": "critical",
                    "response_time_ms": elapsed,
                    "status_code": status_code,
                    "error_message": f"HTTP 404 Not Found",
                }

            if status_code >= 400:
                return {
                    "status": "critical",
                    "response_time_ms": elapsed,
                    "status_code": status_code,
                    "error_message": f"HTTP {status_code} Client Error",
                }

            return {
                "status": "ok",
                "response_time_ms": elapsed,
                "status_code": status_code,
                "error_message": "",
            }
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        logger.error(f"Uptime check failed for {site['url']}: {e}")
        return {
            "status": "critical",
            "response_time_ms": elapsed,
            "status_code": 0,
            "error_message": str(e),
        }


async def _check_indicator(page, indicator: str) -> bool:
    """Check if a success indicator exists on the page.
    Tries multiple strategies: CSS selector, id attribute, URL fragment, page text.
    """
    # Strategy 1: Direct CSS selector (handles #id, .class, [attr], tag, etc.)
    try:
        el = await page.query_selector(indicator)
        if el:
            return True
    except Exception:
        pass

    # Strategy 2: If indicator looks like an id (e.g. "#myElement"), also try
    # by id attribute directly in case the selector engine has issues
    if indicator.startswith("#") and len(indicator) > 1:
        raw_id = indicator[1:]
        try:
            el = await page.query_selector(f'[id="{raw_id}"]')
            if el:
                return True
        except Exception:
            pass
        # Also try case-insensitive id match
        try:
            el = await page.query_selector(f'[id="{raw_id}" i]')
            if el:
                return True
        except Exception:
            pass

    # Strategy 3: If indicator looks like a class (e.g. ".dashboard"), also try
    # by class attribute
    if indicator.startswith(".") and len(indicator) > 1:
        raw_class = indicator[1:]
        try:
            el = await page.query_selector(f'[class*="{raw_class}"]')
            if el:
                return True
        except Exception:
            pass

    # Strategy 4: Check if the current URL contains the indicator text
    current_url = page.url
    clean = indicator.lstrip("#.").lower()
    if clean and clean in current_url.lower():
        return True

    # Strategy 5: Check visible text content on the page
    try:
        body_text = await page.inner_text("body")
        if clean in body_text.lower():
            return True
    except Exception:
        pass

    # Strategy 6: Check full HTML (handles hidden elements, attributes, etc.)
    try:
        html = await page.content()
        if clean in html.lower():
            return True
    except Exception:
        pass

    return False


async def run_login_check(
    site: dict, credentials: dict, pages: list[dict] | None = None
) -> dict:
    """Perform login flow, verify success, then optionally validate subpages."""
    start = time.time()
    page_results = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            bpage = await context.new_page()

            # Navigate to login page
            await bpage.goto(
                credentials["login_url"],
                timeout=settings.BROWSER_TIMEOUT_MS,
                wait_until="domcontentloaded",
            )

            # Fill credentials
            await bpage.fill(
                credentials["username_selector"], credentials["username"]
            )
            await bpage.fill(
                credentials["password_selector"], credentials["password"]
            )

            # Submit and wait for navigation/response
            indicator = (credentials.get("success_indicator") or "").strip()

            if indicator:
                # Click and wait for either a navigation or a network idle
                try:
                    async with bpage.expect_navigation(
                        timeout=10000, wait_until="domcontentloaded"
                    ):
                        await bpage.click(credentials["submit_selector"])
                except Exception:
                    # SPA login — no navigation event, that's okay
                    pass
            else:
                await bpage.click(credentials["submit_selector"])
                try:
                    await bpage.wait_for_load_state(
                        "domcontentloaded", timeout=10000
                    )
                except Exception:
                    pass

            # Wait for page to stabilize (JS rendering, redirects, SPA transitions)
            try:
                await bpage.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            # Extra buffer for slow JS rendering
            await bpage.wait_for_timeout(3000)

            # Verify success indicator
            if indicator:
                found = await _check_indicator(bpage, indicator)
                if not found:
                    # Some sites redirect after login — wait a bit more and retry
                    await bpage.wait_for_timeout(3000)
                    found = await _check_indicator(bpage, indicator)

                if not found:
                    elapsed = (time.time() - start) * 1000
                    current_url = bpage.url
                    await browser.close()
                    return {
                        "status": "critical",
                        "response_time_ms": elapsed,
                        "status_code": 200,
                        "error_message": (
                            f"Login completed but success indicator '{indicator}' "
                            f"not found. Current page: {current_url}"
                        ),
                    }

            # If subpages are configured, validate them after login
            overall_status = "ok"
            if pages:
                for pg in sorted(pages, key=lambda x: x.get("sort_order", 0)):
                    pg_start = time.time()
                    pg_result = {
                        "page_name": pg.get("page_name", pg["page_url"]),
                        "status": "ok",
                        "error": "",
                    }

                    try:
                        await bpage.goto(
                            pg["page_url"],
                            timeout=settings.BROWSER_TIMEOUT_MS,
                            wait_until="domcontentloaded",
                        )

                        if pg.get("expected_element"):
                            try:
                                await bpage.wait_for_selector(
                                    pg["expected_element"], timeout=10000
                                )
                            except Exception:
                                pg_result["status"] = "critical"
                                pg_result["error"] = (
                                    f"Element '{pg['expected_element']}' not found"
                                )
                                overall_status = "critical"

                        if pg.get("expected_text"):
                            content = await bpage.content()
                            if pg["expected_text"] not in content:
                                if pg_result["status"] == "ok":
                                    pg_result["status"] = "warning"
                                pg_result["error"] = (
                                    f"Text '{pg['expected_text']}' not found"
                                )
                                if overall_status == "ok":
                                    overall_status = "warning"

                    except Exception as e:
                        pg_result["status"] = "critical"
                        pg_result["error"] = str(e)
                        overall_status = "critical"

                    pg_result["response_time_ms"] = (time.time() - pg_start) * 1000
                    page_results.append(pg_result)

            elapsed = (time.time() - start) * 1000
            await browser.close()

            return {
                "status": overall_status,
                "response_time_ms": elapsed,
                "status_code": 200,
                "error_message": next(
                    (r["error"] for r in page_results if r["error"]), ""
                ),
                "details": json.dumps(page_results) if page_results else "",
            }
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        logger.error(f"Login check failed for {site['url']}: {e}")
        return {
            "status": "critical",
            "response_time_ms": elapsed,
            "status_code": 0,
            "error_message": str(e),
            "details": json.dumps(page_results) if page_results else "",
        }


async def run_multi_page_check(
    site: dict, credentials: dict, pages: list[dict]
) -> dict:
    """Login then validate multiple pages."""
    start = time.time()
    page_results = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            bpage = await context.new_page()

            # Login first
            if credentials and credentials.get("login_url"):
                await bpage.goto(
                    credentials["login_url"],
                    timeout=settings.BROWSER_TIMEOUT_MS,
                    wait_until="domcontentloaded",
                )
                await bpage.fill(
                    credentials["username_selector"], credentials["username"]
                )
                await bpage.fill(
                    credentials["password_selector"], credentials["password"]
                )
                try:
                    async with bpage.expect_navigation(
                        timeout=10000, wait_until="domcontentloaded"
                    ):
                        await bpage.click(credentials["submit_selector"])
                except Exception:
                    pass
                try:
                    await bpage.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                await bpage.wait_for_timeout(3000)

            # Check each page
            overall_status = "ok"
            for pg in sorted(pages, key=lambda x: x.get("sort_order", 0)):
                pg_start = time.time()
                pg_result = {"page_name": pg.get("page_name", pg["page_url"]), "status": "ok", "error": ""}

                try:
                    await bpage.goto(
                        pg["page_url"],
                        timeout=settings.BROWSER_TIMEOUT_MS,
                        wait_until="domcontentloaded",
                    )

                    if pg.get("expected_element"):
                        try:
                            await bpage.wait_for_selector(pg["expected_element"], timeout=10000)
                        except Exception:
                            pg_result["status"] = "critical"
                            pg_result["error"] = f"Element '{pg['expected_element']}' not found"
                            overall_status = "critical"

                    if pg.get("expected_text"):
                        content = await bpage.content()
                        if pg["expected_text"] not in content:
                            pg_result["status"] = "warning" if pg_result["status"] == "ok" else pg_result["status"]
                            pg_result["error"] = f"Text '{pg['expected_text']}' not found"
                            if overall_status == "ok":
                                overall_status = "warning"

                except Exception as e:
                    pg_result["status"] = "critical"
                    pg_result["error"] = str(e)
                    overall_status = "critical"

                pg_result["response_time_ms"] = (time.time() - pg_start) * 1000
                page_results.append(pg_result)

            elapsed = (time.time() - start) * 1000
            await browser.close()

            return {
                "status": overall_status,
                "response_time_ms": elapsed,
                "status_code": 200,
                "error_message": next(
                    (r["error"] for r in page_results if r["error"]), ""
                ),
                "details": json.dumps(page_results),
            }
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        logger.error(f"Multi-page check failed for {site['url']}: {e}")
        return {
            "status": "critical",
            "response_time_ms": elapsed,
            "status_code": 0,
            "error_message": str(e),
            "details": json.dumps(page_results),
        }
