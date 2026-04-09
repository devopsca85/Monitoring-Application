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
      - "#myId"                          -> already valid
      - ".myClass"                       -> already valid
      - "myId"                           -> try as #myId
      - "myId.table.table-striped"       -> try as #myId.table.table-striped
    """
    selectors = [indicator]

    if not indicator.startswith(("#", ".", "[", "*", ":")):
        selectors.insert(0, f"#{indicator}")

    if "." in indicator and not indicator.startswith(("#", ".")):
        parts = indicator.split(".", 1)
        selectors.insert(0, f"#{parts[0]}.{parts[1]}")

    return selectors


async def _check_indicator_strict(page, indicator: str) -> bool:
    """Check if a success indicator exists on the page using STRICT methods only.
    Only returns True if the element is actually present and visible in the DOM.
    Does NOT check raw HTML text (too many false positives on login pages).
    """
    selectors = _normalize_selector(indicator)

    # Strategy 1: Try all normalized CSS selectors — element must be visible
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                visible = await el.is_visible()
                if visible:
                    logger.info(f"Indicator found (visible): '{sel}'")
                    return True
        except Exception:
            pass

    # Strategy 2: Try all selectors — element exists in DOM (may be hidden)
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                logger.info(f"Indicator found (in DOM): '{sel}'")
                return True
        except Exception:
            pass

    # Strategy 3: Search by ID attribute directly
    raw_id = indicator.split(".")[0].lstrip("#")
    if raw_id:
        try:
            el = await page.query_selector(f'[id="{raw_id}"]')
            if el:
                logger.info(f"Indicator found by id attr: '{raw_id}'")
                return True
        except Exception:
            pass
        # Partial ID match
        try:
            el = await page.query_selector(f'[id*="{raw_id}"]')
            if el:
                logger.info(f"Indicator found by partial id: '{raw_id}'")
                return True
        except Exception:
            pass

    return False


async def _detect_login_failure(page, login_url: str) -> str | None:
    """Detect common signs that a login has failed.
    Returns an error message if failure detected, None otherwise.
    """
    current_url = page.url

    # Check 1: Still on the login page (URL didn't change)
    if current_url.rstrip("/") == login_url.rstrip("/"):
        # Look for common error indicators
        error_selectors = [
            ".error", ".alert-danger", ".alert-error", ".login-error",
            ".validation-summary-errors", ".field-validation-error",
            "#errorMessage", "#error", ".text-danger",
            "[role='alert']", ".invalid-feedback",
        ]
        for sel in error_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    visible = await el.is_visible()
                    if visible:
                        text = (await el.inner_text()).strip()
                        if text:
                            return f"Login failed — error on page: {text[:200]}"
            except Exception:
                pass

        return "Login failed — still on login page after submit"

    # Check 2: Redirected back to login page (different URL format)
    lower_url = current_url.lower()
    login_keywords = ["login", "signin", "sign-in", "auth", "logon"]
    if any(kw in lower_url for kw in login_keywords):
        # Could be redirected to a login page, check for error messages
        try:
            body_text = await page.inner_text("body")
            error_keywords = [
                "invalid", "incorrect", "wrong password", "failed",
                "unauthorized", "denied", "try again", "not recognized",
            ]
            lower_text = body_text.lower()
            for kw in error_keywords:
                if kw in lower_text:
                    return f"Login failed — page contains '{kw}'"
        except Exception:
            pass

    return None


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

            login_url = credentials.get("login_url", "")

            # Navigate to login page
            await bpage.goto(
                login_url,
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

            # Remember the URL before submit
            pre_login_url = bpage.url

            # Submit and wait for navigation/response
            indicator = (credentials.get("success_indicator") or "").strip()

            try:
                async with bpage.expect_navigation(
                    timeout=10000, wait_until="domcontentloaded"
                ):
                    await bpage.click(credentials["submit_selector"])
            except Exception:
                # SPA login — no navigation event, that's okay
                pass

            # Wait for page to stabilize
            try:
                await bpage.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            await bpage.wait_for_timeout(5000)

            # === STEP 1: Detect obvious login failures ===
            failure_msg = await _detect_login_failure(bpage, pre_login_url)

            # If no indicator is set and failure is detected, report it
            if not indicator and failure_msg:
                elapsed = (time.time() - start) * 1000
                await browser.close()
                return {
                    "status": "critical",
                    "response_time_ms": elapsed,
                    "status_code": 200,
                    "error_message": failure_msg,
                }

            # If no indicator is set and no failure detected,
            # check that the URL actually changed (basic login validation)
            if not indicator and not failure_msg:
                post_login_url = bpage.url
                if post_login_url.rstrip("/") == pre_login_url.rstrip("/"):
                    elapsed = (time.time() - start) * 1000
                    await browser.close()
                    return {
                        "status": "warning",
                        "response_time_ms": elapsed,
                        "status_code": 200,
                        "error_message": (
                            "Login may have failed — URL did not change after submit. "
                            "Set a Success Indicator for reliable detection."
                        ),
                    }

            # === STEP 2: Verify success indicator (if set) ===
            if indicator:
                found = await _check_indicator_strict(bpage, indicator)
                if not found:
                    # Wait more and retry once
                    await bpage.wait_for_timeout(5000)
                    found = await _check_indicator_strict(bpage, indicator)

                if not found:
                    elapsed = (time.time() - start) * 1000
                    current_url = bpage.url

                    # Check if it's actually a login failure
                    if failure_msg:
                        error = failure_msg
                    else:
                        error = (
                            f"Login completed but success indicator '{indicator}' "
                            f"not found. Current page: {current_url}"
                        )

                    await browser.close()
                    return {
                        "status": "critical",
                        "response_time_ms": elapsed,
                        "status_code": 200,
                        "error_message": error,
                    }

            # === STEP 3: Validate subpages (if configured) ===
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
