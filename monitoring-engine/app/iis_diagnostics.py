"""
IIS / App Pool Diagnostics
Analyzes page responses, error patterns, and timing to detect IIS-level issues.
Works by examining HTTP headers, response patterns, and error page content.
"""
import logging

logger = logging.getLogger(__name__)

# IIS error signatures and their app pool implications
IIS_ERROR_PATTERNS = [
    # App pool recycle / startup
    {
        "patterns": ["service unavailable", "503 service unavailable", "http error 503"],
        "category": "app_pool_stopped",
        "severity": "critical",
        "diagnosis": "IIS returned 503 — App Pool is stopped or not started",
        "recommendation": "Check App Pool status in IIS Manager. Consider setting Start Mode to 'AlwaysRunning' to prevent cold starts.",
    },
    {
        "patterns": ["application is being started", "application initialization"],
        "category": "app_pool_starting",
        "severity": "warning",
        "diagnosis": "Application is initializing — App Pool may have just recycled",
        "recommendation": "Enable Application Initialization (preload) to warm up the app before serving requests. Set 'preloadEnabled=true' on the site.",
    },
    # Worker process issues
    {
        "patterns": ["502 bad gateway", "bad gateway"],
        "category": "worker_process_crash",
        "severity": "critical",
        "diagnosis": "502 Bad Gateway — IIS worker process may have crashed or is unresponsive",
        "recommendation": "Check Event Viewer for W3WP crash logs. Review App Pool advanced settings: Rapid-Fail Protection, Private Memory Limit.",
    },
    {
        "patterns": ["502.3", "502.5"],
        "category": "worker_process_timeout",
        "severity": "critical",
        "diagnosis": "Worker process timeout — request exceeded processing time limit",
        "recommendation": "Increase 'Idle Timeout' in App Pool settings. Check for long-running database queries or external API calls.",
    },
    # Request queue
    {
        "patterns": ["503.2", "request queue limit"],
        "category": "request_queue_full",
        "severity": "critical",
        "diagnosis": "IIS request queue is full — App Pool cannot handle the load",
        "recommendation": "Increase Queue Length in App Pool settings (default 1000). Consider adding more worker processes or scaling out.",
    },
    # Memory issues
    {
        "patterns": ["out of memory", "outofmemoryexception", "insufficient memory"],
        "category": "memory_exhaustion",
        "severity": "critical",
        "diagnosis": "Application ran out of memory — App Pool worker process memory limit may be hit",
        "recommendation": "Increase Private Memory Limit in App Pool recycling settings. Check for memory leaks in application code. Consider 64-bit App Pool.",
    },
    # ASP.NET specific
    {
        "patterns": ["compilation error", "parser error"],
        "category": "compilation_error",
        "severity": "critical",
        "diagnosis": "ASP.NET compilation error — application code or config issue",
        "recommendation": "Check web.config for errors. Verify all DLLs are deployed correctly. Check Application Event Log.",
    },
    {
        "patterns": ["configuration error", "config error", "web.config"],
        "category": "config_error",
        "severity": "critical",
        "diagnosis": "IIS/ASP.NET configuration error",
        "recommendation": "Review web.config, applicationHost.config. Validate machine key, connection strings, and handler mappings.",
    },
    # Authentication issues
    {
        "patterns": ["401 unauthorized", "401.1", "401.2", "401.3"],
        "category": "auth_misconfigured",
        "severity": "warning",
        "diagnosis": "IIS authentication failure — may indicate misconfigured auth settings",
        "recommendation": "Check IIS Authentication settings: Anonymous, Windows, Forms. Verify App Pool identity has correct permissions.",
    },
    {
        "patterns": ["403 forbidden", "403.14", "directory listing denied"],
        "category": "access_denied",
        "severity": "warning",
        "diagnosis": "IIS access denied — directory browsing disabled or permissions issue",
        "recommendation": "Check NTFS permissions on the site folder. Verify App Pool identity. Check Directory Browsing settings.",
    },
    # SSL/HTTPS
    {
        "patterns": ["403.16", "client certificate", "ssl"],
        "category": "ssl_issue",
        "severity": "warning",
        "diagnosis": "SSL/TLS or client certificate issue in IIS",
        "recommendation": "Check SSL certificate binding in IIS. Verify certificate validity and chain. Check HTTPS bindings.",
    },
]

# Response time patterns that indicate IIS/App Pool issues
TIMING_PATTERNS = [
    {
        "condition": lambda ttfb, total, response: ttfb > 10000 and response < 15000,
        "category": "cold_start",
        "diagnosis": "High TTFB suggests App Pool cold start (JIT compilation, app init)",
        "recommendation": "Set App Pool Start Mode to 'AlwaysRunning'. Enable Application Initialization with preloadEnabled=true. Consider Application Warm-Up module.",
    },
    {
        "condition": lambda ttfb, total, response: ttfb > 5000 and ttfb / max(total, 1) > 0.8,
        "category": "backend_bottleneck",
        "diagnosis": "Server processing is the dominant bottleneck (TTFB is >80% of total load)",
        "recommendation": "Profile server-side code. Check database query performance. Monitor App Pool CPU and memory usage. Consider increasing worker processes.",
    },
    {
        "condition": lambda ttfb, total, response: response > 20000,
        "category": "request_timeout_risk",
        "diagnosis": "Response time is approaching IIS default timeout (default 120s). Risk of 502.3 timeout.",
        "recommendation": "Optimize the slow endpoint. If legitimate long operation, increase IIS request timeout. Consider async processing.",
    },
]


async def analyze_iis_diagnostics(page, response_time_ms: float, perf_summary: dict) -> dict:
    """Analyze page response for IIS/App Pool related issues.

    Args:
        page: Playwright page object (after page load)
        response_time_ms: Total response time
        perf_summary: Performance metrics from perf.py

    Returns:
        dict with:
          has_issues: bool
          issues: list of {category, severity, diagnosis, recommendation}
          iis_analysis: summary string
    """
    result = {
        "has_issues": False,
        "issues": [],
        "iis_analysis": "",
    }

    issues = []

    # 1. Scan page content for IIS error signatures
    try:
        page_html = await page.content()
        page_lower = page_html.lower()

        for pattern_group in IIS_ERROR_PATTERNS:
            for p in pattern_group["patterns"]:
                if p in page_lower:
                    # Extract error text context
                    detail = ""
                    try:
                        body_text = await page.inner_text("body")
                        for line in body_text.split("\n"):
                            if p in line.strip().lower() and 10 < len(line.strip()) < 500:
                                detail = line.strip()[:200]
                                break
                    except Exception:
                        pass

                    issue = {
                        "category": pattern_group["category"],
                        "severity": pattern_group["severity"],
                        "diagnosis": pattern_group["diagnosis"] + (f" — {detail}" if detail else ""),
                        "recommendation": pattern_group["recommendation"],
                    }
                    issues.append(issue)
                    logger.warning(f"IIS issue: {issue['category']} — {issue['diagnosis'][:100]}")
                    break  # One match per group is enough
    except Exception as e:
        logger.warning(f"IIS page scan failed: {e}")

    # 2. Analyze response headers for IIS indicators
    try:
        # Check response status via page
        status_text = await page.evaluate("() => document.title")
        title_lower = (status_text or "").lower()

        if "503" in title_lower or "service unavailable" in title_lower:
            if not any(i["category"] == "app_pool_stopped" for i in issues):
                issues.append({
                    "category": "app_pool_stopped",
                    "severity": "critical",
                    "diagnosis": f"Page title indicates 503: '{status_text}'",
                    "recommendation": "Start the App Pool in IIS Manager. Set Start Mode to 'AlwaysRunning'.",
                })
    except Exception:
        pass

    # 3. Analyze timing patterns
    ttfb = perf_summary.get("ttfb_ms", 0)
    total_load = perf_summary.get("total_load_ms", 0)

    for tp in TIMING_PATTERNS:
        try:
            if tp["condition"](ttfb, total_load, response_time_ms):
                issues.append({
                    "category": tp["category"],
                    "severity": "warning",
                    "diagnosis": tp["diagnosis"],
                    "recommendation": tp["recommendation"],
                })
        except Exception:
            pass

    # 4. Check for resource loading failures that indicate IIS issues
    failed = perf_summary.get("failed_resources", [])
    if len(failed) >= 3:
        issues.append({
            "category": "resource_serving_failure",
            "severity": "warning",
            "diagnosis": f"{len(failed)} resources failed to load — IIS static file serving may be misconfigured",
            "recommendation": "Check IIS MIME types, static content handler, and file permissions. Verify staticContent settings in web.config.",
        })

    # 5. High API call latency may indicate App Pool thread starvation
    slow_apis = perf_summary.get("slow_api_calls", [])
    if len(slow_apis) >= 2:
        avg_api_time = sum(a.get("duration", 0) for a in slow_apis) / len(slow_apis)
        if avg_api_time > 5000:
            issues.append({
                "category": "thread_starvation",
                "severity": "warning",
                "diagnosis": f"{len(slow_apis)} API calls averaging {int(avg_api_time)}ms — possible thread pool exhaustion",
                "recommendation": "Increase maxConcurrentRequestsPerCPU in aspnet.config. Use async/await in API handlers. Check App Pool worker process count.",
            })

    if issues:
        result["has_issues"] = True
        result["issues"] = issues
        # Build summary
        critical_count = sum(1 for i in issues if i["severity"] == "critical")
        warning_count = sum(1 for i in issues if i["severity"] == "warning")
        result["iis_analysis"] = (
            f"{len(issues)} IIS issue(s) detected "
            f"({critical_count} critical, {warning_count} warning)"
        )

    return result
