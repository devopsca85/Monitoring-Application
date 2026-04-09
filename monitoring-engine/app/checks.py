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
                    "error_message": "HTTP 404 Not Found",
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
    selectors = [indicator]
    if not indicator.startswith(("#", ".", "[", "*", ":")):
        selectors.insert(0, f"#{indicator}")
    if "." in indicator and not indicator.startswith(("#", ".")):
        parts = indicator.split(".", 1)
        selectors.insert(0, f"#{parts[0]}.{parts[1]}")
    return selectors


async def _check_indicator_strict(page, indicator: str) -> bool:
    """Check if a success indicator exists using DOM-only methods."""
    selectors = _normalize_selector(indicator)

    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                logger.info(f"Indicator found: '{sel}'")
                return True
        except Exception:
            pass

    raw_id = indicator.split(".")[0].lstrip("#")
    if raw_id:
        for query in [f'[id="{raw_id}"]', f'[id*="{raw_id}"]']:
            try:
                el = await page.query_selector(query)
                if el:
                    logger.info(f"Indicator found by id: '{query}'")
                    return True
            except Exception:
                pass

    return False


async def _detect_login_failure(page, pre_login_url: str) -> str | None:
    """Detect if login failed. Returns error message or None if login looks OK."""
    current_url = page.url
    logger.info(f"Login failure detection: pre_url={pre_login_url}, post_url={current_url}")

    # --- Check A: Is a password field still visible? (strongest signal) ---
    password_selectors = [
        "input[type='password']",
        "input[type='Password']",
        "#PASSWORD", "#password", "#Password",
        "input[name='PASSWORD']", "input[name='password']",
        "input[name='pwd']", "input[name='pass']",
    ]
    for sel in password_selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                visible = await el.is_visible()
                if visible:
                    logger.info(f"Login failure: password field '{sel}' still visible")
                    return "Login failed — password field still visible (wrong credentials?)"
        except Exception:
            pass

    # --- Check B: Look for error messages on the page ---
    error_selectors = [
        ".error", ".alert-danger", ".alert-error", ".login-error",
        ".validation-summary-errors", ".field-validation-error",
        "#errorMessage", "#error", ".text-danger", ".text-error",
        "[role='alert']", ".invalid-feedback",
        "#lblError", "#lblMessage", "#ErrorLabel",
        "span[style*='color:Red']", "span[style*='color: red']",
        "span[style*='color:red']", "span[style*='color:#']",
        ".error-message", "#ctl00_ContentPlaceHolder1_lblError",
    ]
    for sel in error_selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                visible = await el.is_visible()
                if visible:
                    text = (await el.inner_text()).strip()
                    if text:
                        logger.info(f"Login failure: error element '{sel}' = '{text[:100]}'")
                        return f"Login failed — {text[:200]}"
        except Exception:
            pass

    # --- Check C: Look for error keywords in page body ---
    try:
        body_text = await page.inner_text("body")
        error_phrases = [
            "invalid user", "invalid password", "invalid credentials",
            "incorrect password", "incorrect user", "login failed",
            "wrong password", "authentication failed", "access denied",
            "try again", "not recognized", "account locked",
            "user id or password", "invalid logon", "login unsuccessful",
            "unable to log", "bad credentials", "logon failed",
        ]
        lower_text = body_text.lower()
        for phrase in error_phrases:
            if phrase in lower_text:
                logger.info(f"Login failure: page contains '{phrase}'")
                return f"Login failed — page contains: '{phrase}'"
    except Exception:
        pass

    # --- Check D: Look for login form still present ---
    login_form_indicators = [
        "form[name='frmLogon']", "form[id='frmLogon']",
        "form[action*='login']", "form[action*='Login']",
        "form[action*='logon']", "form[action*='Logon']",
        "form[action*='signin']",
    ]
    for sel in login_form_indicators:
        try:
            el = await page.query_selector(sel)
            if el:
                # Form exists — but also check if password field is in it
                pwd = await el.query_selector("input[type='password']")
                if pwd:
                    visible = await pwd.is_visible()
                    if visible:
                        logger.info(f"Login failure: login form '{sel}' with password field still present")
                        return "Login failed — login form still displayed after submit"
        except Exception:
            pass

    logger.info("Login failure detection: no failure signs detected")
    return None


async def run_login_check(
    site: dict, credentials: dict, pages: list[dict] | None = None
) -> dict:
    """Perform login flow, verify success, then optionally validate subpages."""
    start = time.time()
    page_results = []

    # Validate credentials exist
    if not credentials or not credentials.get("login_url"):
        return {
            "status": "critical",
            "response_time_ms": 0,
            "status_code": 0,
            "error_message": "Login check failed — no login URL or credentials configured",
        }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            bpage = await context.new_page()

            login_url = credentials["login_url"]
            logger.info(f"Login check starting: {login_url}")

            # Navigate to login page
            await bpage.goto(
                login_url,
                timeout=settings.BROWSER_TIMEOUT_MS,
                wait_until="domcontentloaded",
            )
            await bpage.wait_for_load_state("networkidle", timeout=10000)

            # Fill credentials
            username_sel = credentials.get("username_selector", "#username")
            password_sel = credentials.get("password_selector", "#password")
            submit_sel = credentials.get("submit_selector", "input[type='submit']")

            logger.info(f"Filling: user='{username_sel}', pass='{password_sel}', submit='{submit_sel}'")

            await bpage.fill(username_sel, credentials.get("username", ""))
            await bpage.fill(password_sel, credentials.get("password", ""))

            # Capture pre-login URL
            pre_login_url = bpage.url
            logger.info(f"Pre-login URL: {pre_login_url}")

            # Submit — wait for full page load (handles ASP.NET postback + redirect)
            try:
                async with bpage.expect_navigation(timeout=20000, wait_until="load"):
                    await bpage.click(submit_sel)
                logger.info(f"Navigation completed after submit")
            except Exception as e:
                logger.info(f"No navigation after submit (SPA?): {e}")

            # Wait for everything to settle
            try:
                await bpage.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            await bpage.wait_for_timeout(5000)

            post_login_url = bpage.url
            logger.info(f"Post-login URL: {post_login_url}")

            # === STEP 1: Detect login failure ===
            failure_msg = await _detect_login_failure(bpage, pre_login_url)

            if failure_msg:
                elapsed = (time.time() - start) * 1000
                logger.warning(f"Login FAILED for {site['url']}: {failure_msg}")
                await browser.close()
                return {
                    "status": "critical",
                    "response_time_ms": elapsed,
                    "status_code": 200,
                    "error_message": failure_msg,
                }

            # === STEP 2: Check expected post-login page ===
            expected_page = (credentials.get("expected_page") or "mainpage.aspx").strip()
            indicator = (credentials.get("success_indicator") or "").strip()
            lower_url = bpage.url.lower()

            # Primary check: did we land on the expected page?
            on_expected_page = expected_page.lower() in lower_url
            logger.info(
                f"Expected page '{expected_page}' in URL '{bpage.url}': {on_expected_page}"
            )

            if on_expected_page:
                # We're on the right page — login succeeded
                # Optionally verify the CSS indicator too
                if indicator:
                    found = await _check_indicator_strict(bpage, indicator)
                    if not found:
                        await bpage.wait_for_timeout(5000)
                        found = await _check_indicator_strict(bpage, indicator)
                    if not found:
                        logger.warning(
                            f"On expected page but indicator '{indicator}' not found — still OK"
                        )
                logger.info(f"Login SUCCESS for {site['url']}, landed on: {bpage.url}")
            else:
                # Not on expected page — try indicator as fallback
                if indicator:
                    found = await _check_indicator_strict(bpage, indicator)
                    if not found:
                        await bpage.wait_for_timeout(5000)
                        found = await _check_indicator_strict(bpage, indicator)

                    if found:
                        logger.info(f"Login SUCCESS for {site['url']} (indicator found)")
                    else:
                        elapsed = (time.time() - start) * 1000
                        await browser.close()
                        return {
                            "status": "critical",
                            "response_time_ms": elapsed,
                            "status_code": 200,
                            "error_message": (
                                f"Login failed — expected '{expected_page}' in URL "
                                f"but got: {bpage.url}. "
                                f"Indicator '{indicator}' also not found."
                            ),
                        }
                else:
                    # No indicator, not on expected page
                    elapsed = (time.time() - start) * 1000
                    await browser.close()
                    return {
                        "status": "critical",
                        "response_time_ms": elapsed,
                        "status_code": 200,
                        "error_message": (
                            f"Login failed — expected '{expected_page}' in URL "
                            f"but got: {bpage.url}"
                        ),
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
        logger.error(f"Login check exception for {site['url']}: {e}")
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
                    credentials.get("username_selector", "#username"),
                    credentials.get("username", ""),
                )
                await bpage.fill(
                    credentials.get("password_selector", "#password"),
                    credentials.get("password", ""),
                )
                try:
                    async with bpage.expect_navigation(
                        timeout=20000, wait_until="load"
                    ):
                        await bpage.click(
                            credentials.get("submit_selector", "input[type='submit']")
                        )
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
                            pg_result["status"] = "warning" if pg_result["status"] == "ok" else pg_result["status"]
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
