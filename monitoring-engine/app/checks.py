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


def _normalize_selector(indicator: str) -> list[str]:
    """Generate a list of CSS selectors to try from user input.

    Users may enter selectors in many formats:
      - "#myId"                          → already valid
      - ".myClass"                       → already valid
      - "myId"                           → try as #myId
      - "myId.table.table-striped"       → try as #myId.table.table-striped
      - "ElementID.class1.class2"        → try as #ElementID.class1.class2
    """
    selectors = [indicator]

    # If it doesn't start with #, ., [, or a known HTML tag prefix,
    # the user likely forgot the # — prepend it
    if not indicator.startswith(("#", ".", "[", "*", ":")):
        selectors.insert(0, f"#{indicator}")

    # If it contains dots, the part before the first dot might be an ID
    # e.g. "TabContainer1_tbTraining.table.table-striped"
    #   → #TabContainer1_tbTraining.table.table-striped
    if "." in indicator and not indicator.startswith(("#", ".")):
        parts = indicator.split(".", 1)
        selectors.insert(0, f"#{parts[0]}.{parts[1]}")

    return selectors


async def _check_indicator(page, indicator: str) -> bool:
    """Check if a success indicator exists on the page.
    Tries multiple strategies: CSS selectors, id/class lookup, URL, page text.
    """
    selectors = _normalize_selector(indicator)

    # Strategy 1: Try all generated CSS selectors
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                return True
        except Exception:
            pass

    # Strategy 2: Extract the ID part and search by attribute
    # Handles "MyId.class1.class2" → look for [id="MyId"]
    raw_id = indicator.split(".")[0].lstrip("#")
    if raw_id:
        try:
            el = await page.query_selector(f'[id="{raw_id}"]')
            if el:
                return True
        except Exception:
            pass
        try:
            el = await page.query_selector(f'[id*="{raw_id}"]')
            if el:
                return True
        except Exception:
            pass

    # Strategy 3: Check if any element's id contains the indicator text
    try:
        el = await page.query_selector(f'[id*="{raw_id}" i]')
        if el:
            return True
    except Exception:
        pass

    # Strategy 4: Check if the current URL contains the indicator text
    clean = indicator.lstrip("#.").split(".")[0].lower()
    current_url = page.url
    if clean and clean in current_url.lower():
        return True

    # Strategy 5: Check full HTML source for the id/class string
    try:
        html = await page.content()
        # Look for the raw indicator text in HTML (id="...", class="...", etc.)
        if indicator.lower() in html.lower():
            return True
        if raw_id.lower() in html.lower():
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
            await bpage.wait_for_timeout(5000)

            # Verify success indicator
            if indicator:
                found = await _check_indicator(bpage, indicator)
                if not found:
                    # Some sites redirect after login — wait a bit more and retry
                    await bpage.wait_for_timeout(5000)
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
                await bpage.wait_for_timeout(5000)

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
