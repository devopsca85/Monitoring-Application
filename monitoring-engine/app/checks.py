import json
import logging
import time

from playwright.async_api import async_playwright

from app.config import settings
from app.perf import collect_performance_metrics, format_perf_summary
from app.iis_diagnostics import analyze_iis_diagnostics

logger = logging.getLogger(__name__)


def _err(component: str, what: str, expected: str = "", actual: str = "", fix: str = "") -> str:
    """Build a structured, readable error message.

    Args:
        component: What failed (LOGIN_FORM, PAGE_ELEMENT, API, BACKEND, IIS, etc.)
        what: What happened
        expected: What was expected (optional)
        actual: What was found instead (optional)
        fix: Suggested action (optional)
    """
    parts = [f"[{component}] {what}"]
    if expected:
        parts.append(f"Expected: {expected}")
    if actual:
        parts.append(f"Actual: {actual}")
    if fix:
        parts.append(f"Action: {fix}")
    return " | ".join(parts)


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

            # Collect performance metrics
            perf = await collect_performance_metrics(page)
            perf_summary = format_perf_summary(perf, settings.MONITOR_REGION)

            # IIS diagnostics for uptime checks
            iis_result = await analyze_iis_diagnostics(page, elapsed, perf_summary)
            if iis_result["has_issues"]:
                perf_summary["iis_diagnostics"] = iis_result["issues"]
                perf_summary["iis_analysis"] = iis_result["iis_analysis"]

            await browser.close()

            iis_hint = f" ({iis_result['issues'][0]['diagnosis'][:80]})" if iis_result.get("has_issues") else ""

            if status_code >= 500:
                return {
                    "status": "critical",
                    "response_time_ms": elapsed,
                    "status_code": status_code,
                    "error_message": _err("SERVER", f"HTTP {status_code} Server Error on {site['url']}", fix=f"Check IIS logs and Application Event Log{iis_hint}"),
                    "details": json.dumps({"perf": perf_summary}),
                }

            if status_code == 404:
                return {
                    "status": "critical",
                    "response_time_ms": elapsed,
                    "status_code": status_code,
                    "error_message": _err("PAGE", f"HTTP 404 Not Found", expected=site['url'], fix="Verify URL is correct and page exists on the server"),
                }

            if status_code >= 400:
                return {
                    "status": "critical",
                    "response_time_ms": elapsed,
                    "status_code": status_code,
                    "error_message": _err("SERVER", f"HTTP {status_code} Client Error on {site['url']}", fix="Check server config, authentication, and access permissions"),
                    "details": json.dumps({"perf": perf_summary}),
                }

            return {
                "status": "ok",
                "response_time_ms": elapsed,
                "status_code": status_code,
                "error_message": "",
                "details": json.dumps({"perf": perf_summary}),
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
    """Generate CSS selectors to try from user input.

    Handles all formats:
      "#myId"                         -> [#myId]
      ".myClass"                      -> [.myClass]
      "ul#breadcrumbs"                -> [ul#breadcrumbs]  (already valid)
      "div.container"                 -> [div.container]   (already valid)
      "input[type='text']"            -> [input[type='text']]
      "myId"                          -> [#myId, myId]     (plain word = try as ID)
      "myId.table.striped"            -> [#myId.table.striped, myId.table.striped]
    """
    selectors = [indicator]

    # If it contains any CSS combinator characters, it's already a proper selector
    has_combinator = any(c in indicator for c in ('#', '.', '[', ':', '>', '+', '~', ' '))

    if has_combinator:
        # Already a valid CSS selector like "ul#breadcrumbs" or "div.class"
        # Only add #-prefixed version if it's a plain word with dots (like "myId.class")
        if '.' in indicator and '#' not in indicator and not indicator[0].isalpha():
            pass  # e.g. ".myClass" — already valid
        elif '.' in indicator and '#' not in indicator and '[' not in indicator:
            # Could be "tabName.class1.class2" — also try as #tabName.class1.class2
            parts = indicator.split(".", 1)
            if parts[0].isidentifier():
                selectors.append(f"#{parts[0]}.{parts[1]}")
        return selectors

    # Plain word without any CSS characters — try as #id first, then as-is
    selectors.insert(0, f"#{indicator}")
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


async def _detect_db_issues(page, response_time_ms: float) -> dict:
    """Detect SQL Server / database related issues on the page.

    Returns dict with:
      is_db_issue: bool
      diagnosis: str (human-readable)
      category: str (timeout, connection, deadlock, slow_query, latency)
    """
    result = {"is_db_issue": False, "diagnosis": "", "category": ""}

    # 1. Check page for SQL / database error messages
    try:
        page_html = await page.content()
        page_lower = page_html.lower()

        sql_error_patterns = [
            # SQL Server specific
            ("sqlexception", "SQL Server exception"),
            ("sql server", "SQL Server error"),
            ("sqlclient", "SQL Client error"),
            ("system.data.sqlclient", "SQL Server connection error"),
            ("execution timeout expired", "SQL query timeout"),
            ("timeout expired", "Database timeout"),
            ("the wait operation timed out", "Database wait timeout"),
            ("a transport-level error", "SQL Server transport error"),
            ("cannot open database", "Database connection failed"),
            ("login failed for user", "Database authentication failed"),
            ("deadlock", "SQL Server deadlock detected"),
            ("transaction was deadlocked", "SQL deadlock victim"),
            ("connection was forcibly closed", "Database connection dropped"),
            ("the underlying provider failed on open", "Database connection failure"),
            ("a network-related or instance-specific error", "SQL Server unreachable"),
            ("server is not found or not accessible", "SQL Server not accessible"),
            ("connection pool", "Database connection pool exhausted"),
            ("max pool size was reached", "Connection pool exhausted"),
            # Generic database
            ("database error", "Database error"),
            ("database is unavailable", "Database unavailable"),
            ("database connection", "Database connection issue"),
            ("db connection", "Database connection issue"),
            ("internal server error", None),  # Check further
            ("500", None),  # Generic, needs context
            # ASP.NET specific
            ("server error in", "ASP.NET server error"),
            ("runtime error", "ASP.NET runtime error"),
            ("unhandled exception", "Unhandled server exception"),
            ("yellow screen of death", "ASP.NET error page"),
            ("stack trace:", "Server stack trace visible"),
        ]

        for pattern, desc in sql_error_patterns:
            if pattern in page_lower:
                if desc:
                    result["is_db_issue"] = True
                    result["diagnosis"] = desc
                    # Categorize
                    if "timeout" in pattern or "timed out" in pattern:
                        result["category"] = "timeout"
                    elif "deadlock" in pattern:
                        result["category"] = "deadlock"
                    elif "connection" in pattern or "pool" in pattern or "open" in pattern:
                        result["category"] = "connection"
                    elif "login failed" in pattern:
                        result["category"] = "db_auth"
                    else:
                        result["category"] = "sql_error"

                    # Try to extract the actual error text
                    try:
                        body_text = await page.inner_text("body")
                        for line in body_text.split("\n"):
                            line_lower = line.strip().lower()
                            if pattern in line_lower and len(line.strip()) < 500:
                                result["diagnosis"] = f"{desc}: {line.strip()[:200]}"
                                break
                    except Exception:
                        pass

                    logger.warning(f"DB issue detected: {result['category']} — {result['diagnosis']}")
                    return result
    except Exception as e:
        logger.warning(f"DB issue detection page scan failed: {e}")

    # 2. Analyze response time for backend latency indicators
    if response_time_ms > 15000:
        # Very slow response — likely database/backend issue
        result["is_db_issue"] = True
        result["category"] = "latency"
        result["diagnosis"] = (
            f"Severe backend latency detected — login took {int(response_time_ms)}ms. "
            f"This typically indicates SQL Server query delays, connection pool exhaustion, "
            f"or heavy database load."
        )
        logger.warning(f"Backend latency: {int(response_time_ms)}ms — likely DB issue")
    elif response_time_ms > 8000:
        # Moderately slow — possible DB issue
        result["category"] = "latency"
        result["diagnosis"] = (
            f"Elevated backend latency — login took {int(response_time_ms)}ms. "
            f"May indicate database slowness or backend processing delays."
        )
        # Not flagged as is_db_issue for moderate — just informational

    return result


async def _detect_error_page_redirect(page, post_url: str, pre_url: str, response_ms: float) -> dict | None:
    """Detect if login redirected to an error page instead of the expected page.

    Checks for known error pages like GenericError.aspx, Error.aspx, etc.
    Returns a full result dict if error page detected, None otherwise.
    """
    lower_url = post_url.lower()

    # Known error page patterns — add more as discovered
    error_pages = [
        ("genericerror.aspx", "GenericError.aspx", "Application error — possible code or configuration issue"),
        ("generic_error", "GenericError", "Application error — possible code or configuration issue"),
        ("error.aspx", "Error.aspx", "Application error page"),
        ("errorpage.aspx", "ErrorPage.aspx", "Application error page"),
        ("apperror.aspx", "AppError.aspx", "Application error"),
        ("servererror.aspx", "ServerError.aspx", "Server error page"),
        ("500.aspx", "500.aspx", "HTTP 500 error page"),
        ("500.html", "500.html", "HTTP 500 error page"),
        ("oops", "Oops page", "Application error"),
        ("something-went-wrong", "Something went wrong", "Application error"),
        ("accessdenied.aspx", "AccessDenied.aspx", "Access denied — possible permission or role issue"),
        ("unauthorized.aspx", "Unauthorized.aspx", "Unauthorized access"),
        ("sessionexpired.aspx", "SessionExpired.aspx", "Session expired during login"),
        ("maintenance.aspx", "Maintenance.aspx", "Site is under maintenance"),
        ("offline.aspx", "Offline.aspx", "Site is offline"),
    ]

    for pattern, page_name, base_desc in error_pages:
        if pattern in lower_url:
            logger.error(f"Error page redirect detected: {post_url} (pattern: {pattern})")

            # Try to extract error details from the page
            error_detail = ""
            try:
                body_text = await page.inner_text("body")
                # Clean and truncate
                clean_text = " ".join(body_text.split())[:500]
                if clean_text and len(clean_text) > 20:
                    error_detail = clean_text
            except Exception:
                pass

            # Try to find specific error elements
            error_element_text = ""
            for sel in [".error-message", "#errorMessage", ".error", "#error",
                        ".alert-danger", "[role='alert']", "h1", "h2", ".content", "#content"]:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        txt = (await el.inner_text()).strip()
                        if txt and len(txt) > 10 and len(txt) < 500:
                            error_element_text = txt
                            break
                except Exception:
                    pass

            # Build diagnostic message
            diagnosis = f"Post-login redirect to {page_name} — {base_desc}"
            if error_element_text:
                diagnosis += f". Page says: \"{error_element_text[:200]}\""

            error_msg = _err(
                "APPLICATION",
                f"Redirected to {page_name} after login — {base_desc}",
                expected="Post-login redirect to application page",
                actual=f"URL: {post_url}" + (f" — Page: {error_element_text[:150]}" if error_element_text else ""),
                fix="Check Application Event Log, web.config, and recent deployments",
            )

            return {
                "status": "critical",
                "response_time_ms": response_ms,
                "status_code": 200,
                "error_message": error_msg,
                "details": json.dumps({
                    "error_page_redirect": True,
                    "error_page": page_name,
                    "expected_url_changed": pre_url != post_url,
                    "post_login_url": post_url,
                    "diagnosis": diagnosis,
                    "page_error_text": error_element_text[:300] if error_element_text else "",
                    "page_body_preview": error_detail[:300] if error_detail else "",
                    "response_time_ms": int(response_ms),
                    "region": settings.MONITOR_REGION,
                }),
            }

    return None


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
                    return _err("LOGIN_AUTH", "Password field still visible after submit — login rejected", expected="Redirect to post-login page", actual=f"Still on: {page.url}", fix="Verify username/password credentials in site config")
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
                        return _err("LOGIN_AUTH", f"Login error displayed: {text[:150]}", actual=f"Error element: {sel}", fix="Check credentials or application error handling")
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
                return _err("LOGIN_AUTH", f"Error keyword detected on page: '{phrase}'", actual=f"Page: {page.url}", fix="Verify credentials. Check if account is locked or expired")
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
                        return _err("LOGIN_FORM", "Login form still displayed after submit — login did not process", actual=f"Form: {sel} still on page", fix="Check if submit button selector is correct. Server may not have processed the login")
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

            # Fill credentials
            username_sel = credentials.get("username_selector", "#username")
            password_sel = credentials.get("password_selector", "#password")
            submit_sel = credentials.get("submit_selector", "input[type='submit']")

            try:
                await bpage.fill(username_sel, credentials.get("username", ""))
            except Exception as e:
                await browser.close()
                return {
                    "status": "critical",
                    "response_time_ms": (time.time() - start) * 1000,
                    "status_code": 0,
                    "error_message": _err("LOGIN_FORM", f"Username field not found on login page", expected=f"Selector: {username_sel}", actual=f"Page: {login_url}", fix=f"Verify selector in site config. Site may be down or page structure changed. ({str(e).split(chr(10))[0][:100]})"),
                }

            try:
                await bpage.fill(password_sel, credentials.get("password", ""))
            except Exception as e:
                await browser.close()
                return {
                    "status": "critical",
                    "response_time_ms": (time.time() - start) * 1000,
                    "status_code": 0,
                    "error_message": _err("LOGIN_FORM", f"Password field not found on login page", expected=f"Selector: {password_sel}", actual=f"Page: {login_url}", fix=f"Verify selector in site config. ({str(e).split(chr(10))[0][:100]})"),
                }

            # Capture pre-login URL
            pre_login_url = bpage.url

            # ---- START measuring actual response time ----
            response_start = time.time()
            nav_succeeded = False

            # Submit and wait for navigation (FIX #1: log failures, don't silently swallow)
            try:
                async with bpage.expect_navigation(timeout=20000, wait_until="load"):
                    await bpage.click(submit_sel)
                nav_succeeded = True
            except Exception as nav_err:
                logger.warning(f"Navigation after submit: {type(nav_err).__name__}: {str(nav_err)[:100]}")

            # Wait for network to settle
            try:
                await bpage.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass

            # ---- END measuring actual response time ----
            actual_response_ms = (time.time() - response_start) * 1000
            logger.info(f"Response time: {int(actual_response_ms)}ms, nav={nav_succeeded}")

            # Buffer for JS rendering (NOT counted in response time)
            await bpage.wait_for_timeout(2000)

            post_login_url = bpage.url
            logger.info(f"Post-login URL: {post_login_url}")

            # FIX #1: If no navigation AND URL unchanged, form submit likely failed
            if not nav_succeeded and post_login_url.rstrip("/") == pre_login_url.rstrip("/"):
                logger.warning(f"Form submit may have failed — no navigation, URL unchanged")

            # === PRE-CHECK: Detect error page redirects ===
            error_page_result = await _detect_error_page_redirect(
                bpage, post_login_url, pre_login_url, actual_response_ms
            )
            if error_page_result:
                await browser.close()
                return error_page_result

            # === STEP 0: Check for database / SQL Server issues ===
            db_check = await _detect_db_issues(bpage, actual_response_ms)

            if db_check["is_db_issue"]:
                category = db_check["category"]
                diagnosis = db_check["diagnosis"]
                error_msg = _err("DATABASE", f"{category.upper()} — {diagnosis}", fix="Check SQL Server logs, connection strings, and App Pool health")
                logger.error(f"DB issue for {site['url']}: {error_msg}")
                await browser.close()
                return {
                    "status": "critical",
                    "response_time_ms": actual_response_ms,
                    "status_code": 200,
                    "error_message": error_msg,
                    "details": json.dumps({
                        "db_issue": True, "db_category": category,
                        "db_diagnosis": diagnosis,
                        "response_time_ms": int(actual_response_ms),
                        "region": settings.MONITOR_REGION,
                    }),
                }

            # === STEP 1: Detect login failure ===
            failure_msg = await _detect_login_failure(bpage, pre_login_url)

            if failure_msg:
                if actual_response_ms > 8000 and db_check.get("diagnosis"):
                    failure_msg = f"{failure_msg} | [BACKEND] Possible DB latency: {db_check['diagnosis']}"

                logger.warning(f"Login FAILED for {site['url']}: {failure_msg}")
                await browser.close()
                return {
                    "status": "critical",
                    "response_time_ms": actual_response_ms,
                    "status_code": 200,
                    "error_message": failure_msg,
                    "details": json.dumps({
                        "db_latency_note": db_check.get("diagnosis", ""),
                        "response_time_ms": int(actual_response_ms),
                        "region": settings.MONITOR_REGION,
                    }) if db_check.get("diagnosis") else "",
                }

            # === STEP 2: Check expected post-login page ===
            expected_page = (credentials.get("expected_page") or "mainpage.aspx").strip()
            indicator = (credentials.get("success_indicator") or "").strip()
            lower_url = bpage.url.lower()

            on_expected_page = expected_page.lower() in lower_url
            logger.info(f"Expected page '{expected_page}' in URL '{bpage.url}': {on_expected_page}")

            # FIX #2: Indicator check must PASS if configured — no false success
            if indicator:
                found = await _check_indicator_strict(bpage, indicator)
                if not found:
                    # One retry after short wait — no extra 2s inflating response time (FIX #3)
                    await bpage.wait_for_timeout(1000)
                    found = await _check_indicator_strict(bpage, indicator)

                if found:
                    logger.info(f"Login SUCCESS for {site['url']} (indicator '{indicator}' found)")
                elif on_expected_page:
                    # On expected page but indicator missing — WARN, not silent pass
                    logger.warning(f"On expected page but indicator '{indicator}' NOT found")
                    # Still treat as OK since the page loaded — but log for investigation
                else:
                    await browser.close()
                    return {
                        "status": "critical",
                        "response_time_ms": actual_response_ms,
                        "status_code": 200,
                        "error_message": _err("PAGE_ELEMENT", f"Success indicator not found after login", expected=f"Element: {indicator} on page: {expected_page}", actual=f"Current URL: {bpage.url}", fix="Verify CSS selector in site config. Page may have changed structure or login may have silently failed"),
                    }
            elif on_expected_page:
                logger.info(f"Login SUCCESS for {site['url']}, landed on: {bpage.url}")
            else:
                await browser.close()
                return {
                    "status": "critical",
                    "response_time_ms": actual_response_ms,
                    "status_code": 200,
                    "error_message": _err("LOGIN", f"Post-login page mismatch", expected=f"URL containing: {expected_page}", actual=f"URL: {bpage.url}", fix="Check expected page setting. Login may have failed or app may have redirected elsewhere"),
                }

            # Collect performance metrics
            login_perf = await collect_performance_metrics(bpage)
            login_perf_summary = format_perf_summary(login_perf, settings.MONITOR_REGION)

            if db_check.get("diagnosis"):
                login_perf_summary["db_latency_note"] = db_check["diagnosis"]
                login_perf_summary["db_category"] = db_check.get("category", "")

            # Bottleneck analysis
            ttfb = login_perf_summary.get("ttfb_ms", 0)
            total_load = login_perf_summary.get("total_load_ms", 0)
            if ttfb > 0 and total_load > 0:
                backend_pct = round((ttfb / total_load) * 100)
                login_perf_summary["backend_time_pct"] = backend_pct
                if ttfb > 5000:
                    login_perf_summary["bottleneck"] = "backend/database"
                    login_perf_summary["bottleneck_detail"] = (
                        f"TTFB is {ttfb}ms ({backend_pct}% of total) — server/database bottleneck"
                    )
                elif total_load - ttfb > 5000:
                    login_perf_summary["bottleneck"] = "frontend/rendering"
                    login_perf_summary["bottleneck_detail"] = (
                        f"Frontend took {total_load - ttfb}ms after response — rendering bottleneck"
                    )

            # === IIS / App Pool Diagnostics ===
            iis_result = await analyze_iis_diagnostics(bpage, actual_response_ms, login_perf_summary)
            if iis_result["has_issues"]:
                login_perf_summary["iis_diagnostics"] = iis_result["issues"]
                login_perf_summary["iis_analysis"] = iis_result["iis_analysis"]
                logger.info(f"IIS diagnostics for {site['url']}: {iis_result['iis_analysis']}")

            # === STEP 3: Validate subpages ===
            overall_status = "ok"
            if pages:
                from urllib.parse import urlparse
                for pg in sorted(pages, key=lambda x: x.get("sort_order", 0)):
                    pg_start = time.time()
                    pg_result = {"page_name": pg.get("page_name", pg["page_url"]), "status": "ok", "error": ""}

                    try:
                        resp = await bpage.goto(pg["page_url"], timeout=settings.BROWSER_TIMEOUT_MS, wait_until="domcontentloaded")
                        await bpage.wait_for_timeout(1500)

                        status_code = resp.status if resp else 0
                        if status_code >= 400:
                            pg_result["status"] = "critical"
                            pg_result["error"] = _err("SERVER", f"HTTP {status_code}", expected=f"200 OK for {pg['page_url']}", fix="Check if page exists and server is running")
                            overall_status = "critical"
                            pg_result["response_time_ms"] = (time.time() - pg_start) * 1000
                            page_results.append(pg_result)
                            continue

                        actual_url = bpage.url.lower()
                        if any(kw in actual_url for kw in ["login", "signin", "logon", "auth"]):
                            pg_result["status"] = "critical"
                            pg_result["error"] = _err("SESSION", "Redirected to login page — session expired or auth failed", expected=pg["page_url"], actual=bpage.url, fix="Check session timeout settings, cookie config, and IIS authentication")
                            overall_status = "critical"
                        elif any(kw in actual_url for kw in ["error", "404", "not-found", "genericerror"]):
                            pg_result["status"] = "critical"
                            pg_result["error"] = _err("APPLICATION", "Redirected to error page", expected=pg["page_url"], actual=bpage.url, fix="Check Application Event Log and web.config customErrors")
                            overall_status = "critical"
                        else:
                            exp_path = urlparse(pg["page_url"]).path.rstrip("/")
                            act_path = urlparse(bpage.url).path.rstrip("/")
                            if exp_path != act_path and not pg.get("expected_element"):
                                pg_result["status"] = "warning"
                                pg_result["error"] = _err("ROUTING", "URL path mismatch after navigation", expected=exp_path, actual=act_path, fix="Verify page URL. SPA may be routing to a different view")
                                if overall_status == "ok":
                                    overall_status = "warning"

                        if pg.get("expected_element"):
                            selectors = _normalize_selector(pg["expected_element"].strip())
                            found = False
                            for sel in selectors:
                                try:
                                    el = await bpage.query_selector(sel)
                                    if el:
                                        found = True
                                        break
                                except Exception:
                                    pass
                            if not found:
                                pg_result["status"] = "critical"
                                pg_result["error"] = _err("PAGE_ELEMENT", f"CSS selector not found on page", expected=f"Element: {pg['expected_element']}", actual=f"Page: {bpage.url}", fix="Verify selector matches current page. Element may have been renamed or removed")
                                overall_status = "critical"

                        if pg.get("expected_text"):
                            content = await bpage.content()
                            if pg["expected_text"] not in content:
                                if pg_result["status"] == "ok":
                                    pg_result["status"] = "warning"
                                pg_result["error"] = _err("PAGE_CONTENT", f"Expected text not found", expected=f"Text: '{pg['expected_text']}'", actual=f"Page: {bpage.url}", fix="Page content may have changed or loaded incompletely")
                                if overall_status == "ok":
                                    overall_status = "warning"

                        if not pg.get("expected_element") and not pg.get("expected_text"):
                            try:
                                body = await bpage.inner_text("body")
                                if len(body.strip()) < 50:
                                    pg_result["status"] = "warning"
                                    pg_result["error"] = _err("PAGE_CONTENT", "Page body has very little content — may be blank or error page", actual=f"Page: {bpage.url}", fix="Add a CSS selector check for this page to validate content")
                                    if overall_status == "ok":
                                        overall_status = "warning"
                            except Exception:
                                pass

                    except Exception as e:
                        pg_result["status"] = "critical"
                        pg_result["error"] = str(e).split("\n")[0][:200]
                        overall_status = "critical"

                    pg_result["response_time_ms"] = (time.time() - pg_start) * 1000
                    page_results.append(pg_result)

            await browser.close()

            return {
                "status": overall_status,
                "response_time_ms": actual_response_ms,
                "status_code": 200,
                "error_message": next((r["error"] for r in page_results if r["error"]), ""),
                "details": json.dumps({"perf": login_perf_summary, "subpages": page_results}),
            }
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        logger.error(f"Login check exception for {site['url']}: {e}", exc_info=True)
        return {
            "status": "critical",
            "response_time_ms": elapsed,
            "status_code": 0,
            "error_message": str(e).split("\n")[0][:200],
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
                    await bpage.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                await bpage.wait_for_timeout(2000)

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
