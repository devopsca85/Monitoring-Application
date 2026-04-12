"""
DAST Security Scanner
Scans websites for common security issues using HTTP headers, SSL, cookies, and page content.
Designed for SMBs — catches the most impactful issues without requiring source code access.
"""
import logging
import ssl
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Security header checks
SECURITY_HEADERS = {
    "strict-transport-security": {
        "title": "Missing HSTS Header",
        "severity": "high",
        "category": "Transport Security",
        "desc": "Strict-Transport-Security header not set. Users can be downgraded to HTTP.",
        "rec": "Add 'Strict-Transport-Security: max-age=31536000; includeSubDomains' header.",
    },
    "content-security-policy": {
        "title": "Missing Content-Security-Policy",
        "severity": "medium",
        "category": "XSS Protection",
        "desc": "No CSP header. Site is vulnerable to XSS attacks via inline scripts.",
        "rec": "Implement a Content-Security-Policy header. Start with report-only mode.",
    },
    "x-content-type-options": {
        "title": "Missing X-Content-Type-Options",
        "severity": "medium",
        "category": "MIME Sniffing",
        "desc": "Browser may interpret files as different MIME types, enabling attacks.",
        "rec": "Add 'X-Content-Type-Options: nosniff' header.",
    },
    "x-frame-options": {
        "title": "Missing X-Frame-Options",
        "severity": "medium",
        "category": "Clickjacking",
        "desc": "Site can be embedded in iframes, enabling clickjacking attacks.",
        "rec": "Add 'X-Frame-Options: DENY' or 'SAMEORIGIN' header.",
    },
    "x-xss-protection": {
        "title": "Missing X-XSS-Protection",
        "severity": "low",
        "category": "XSS Protection",
        "desc": "Legacy XSS protection header not set (still useful for older browsers).",
        "rec": "Add 'X-XSS-Protection: 1; mode=block' header.",
    },
    "referrer-policy": {
        "title": "Missing Referrer-Policy",
        "severity": "low",
        "category": "Privacy",
        "desc": "Browser may leak referrer information to third parties.",
        "rec": "Add 'Referrer-Policy: strict-origin-when-cross-origin' header.",
    },
    "permissions-policy": {
        "title": "Missing Permissions-Policy",
        "severity": "low",
        "category": "Feature Control",
        "desc": "No control over which browser features the site can use.",
        "rec": "Add Permissions-Policy header to restrict camera, microphone, geolocation access.",
    },
}

# Dangerous headers that should NOT be present
DANGEROUS_HEADERS = {
    "server": {
        "title": "Server Version Exposed",
        "severity": "low",
        "category": "Information Disclosure",
        "desc": "Server header reveals technology and version ({value}). Helps attackers target known vulnerabilities.",
        "rec": "Remove or genericize the Server header.",
    },
    "x-powered-by": {
        "title": "Technology Stack Exposed",
        "severity": "low",
        "category": "Information Disclosure",
        "desc": "X-Powered-By header reveals: {value}. Helps attackers identify framework-specific vulnerabilities.",
        "rec": "Remove the X-Powered-By header in server configuration.",
    },
    "x-aspnet-version": {
        "title": "ASP.NET Version Exposed",
        "severity": "medium",
        "category": "Information Disclosure",
        "desc": "X-AspNet-Version header reveals: {value}.",
        "rec": "Disable in web.config: <httpRuntime enableVersionHeader='false' />",
    },
    "x-aspnetmvc-version": {
        "title": "ASP.NET MVC Version Exposed",
        "severity": "low",
        "category": "Information Disclosure",
        "desc": "X-AspNetMvc-Version header reveals: {value}.",
        "rec": "Remove in Global.asax: MvcHandler.DisableMvcResponseHeader = true",
    },
}


async def scan_site_security(url: str) -> dict:
    """Run a full security scan on a URL."""
    findings = []
    headers_data = {}
    ssl_data = {}
    parsed = urlparse(url)
    hostname = parsed.hostname
    is_https = parsed.scheme == "https"

    # 1. HTTP Request + Header Analysis
    try:
        async with httpx.AsyncClient(follow_redirects=True, verify=False, timeout=15) as client:
            resp = await client.get(url)
            headers_data = dict(resp.headers)
            resp_lower = {k.lower(): v for k, v in resp.headers.items()}

            # Check missing security headers
            for header, info in SECURITY_HEADERS.items():
                if header not in resp_lower:
                    findings.append({
                        "category": info["category"],
                        "severity": info["severity"],
                        "title": info["title"],
                        "description": info["desc"],
                        "recommendation": info["rec"],
                    })

            # Check dangerous headers
            for header, info in DANGEROUS_HEADERS.items():
                if header in resp_lower:
                    val = resp_lower[header]
                    findings.append({
                        "category": info["category"],
                        "severity": info["severity"],
                        "title": info["title"],
                        "description": info["desc"].replace("{value}", val),
                        "recommendation": info["rec"],
                    })

            # Check cookies
            for cookie_header in resp.headers.get_list("set-cookie"):
                cookie_lower = cookie_header.lower()
                cookie_name = cookie_header.split("=")[0].strip()

                if "secure" not in cookie_lower and is_https:
                    findings.append({
                        "category": "Cookie Security",
                        "severity": "medium",
                        "title": f"Cookie '{cookie_name}' Missing Secure Flag",
                        "description": "Cookie can be sent over unencrypted HTTP connections.",
                        "recommendation": "Add 'Secure' flag to all cookies.",
                    })

                if "httponly" not in cookie_lower:
                    findings.append({
                        "category": "Cookie Security",
                        "severity": "medium",
                        "title": f"Cookie '{cookie_name}' Missing HttpOnly Flag",
                        "description": "Cookie accessible via JavaScript — vulnerable to XSS theft.",
                        "recommendation": "Add 'HttpOnly' flag to session cookies.",
                    })

                if "samesite" not in cookie_lower:
                    findings.append({
                        "category": "Cookie Security",
                        "severity": "low",
                        "title": f"Cookie '{cookie_name}' Missing SameSite Attribute",
                        "description": "Cookie may be sent in cross-site requests (CSRF risk).",
                        "recommendation": "Add 'SameSite=Lax' or 'SameSite=Strict' attribute.",
                    })

            # Check for HTTP to HTTPS redirect
            if not is_https:
                findings.append({
                    "category": "Transport Security",
                    "severity": "critical",
                    "title": "Site Not Using HTTPS",
                    "description": "The site is served over unencrypted HTTP.",
                    "recommendation": "Enable HTTPS with a valid SSL certificate and redirect HTTP to HTTPS.",
                })

            # Check for common sensitive paths exposed
            sensitive_paths = ["/wp-admin/", "/.env", "/.git/", "/phpinfo.php", "/server-status", "/elmah.axd"]
            for path in sensitive_paths:
                try:
                    check_resp = await client.get(f"{parsed.scheme}://{parsed.netloc}{path}", follow_redirects=False)
                    if check_resp.status_code == 200:
                        findings.append({
                            "category": "Information Disclosure",
                            "severity": "high" if path in ("/.env", "/.git/") else "medium",
                            "title": f"Sensitive Path Accessible: {path}",
                            "description": f"{path} returned HTTP 200. May expose sensitive information.",
                            "recommendation": f"Block access to {path} in server configuration.",
                        })
                except Exception:
                    pass

            # Check page content for sensitive data exposure
            body = resp.text[:50000]
            body_lower = body.lower()

            if "password" in body_lower and ("type=\"text\"" in body_lower or "type='text'" in body_lower):
                findings.append({
                    "category": "Sensitive Data",
                    "severity": "high",
                    "title": "Password Field Not Using type='password'",
                    "description": "A password field may be using type='text', exposing passwords on screen.",
                    "recommendation": "Change all password inputs to type='password'.",
                })

            if any(pattern in body_lower for pattern in ["api_key", "apikey", "api-key", "secret_key", "secretkey"]):
                findings.append({
                    "category": "Sensitive Data",
                    "severity": "critical",
                    "title": "Potential API Key/Secret Exposed in Page Source",
                    "description": "Page HTML contains patterns that look like API keys or secrets.",
                    "recommendation": "Move secrets to server-side environment variables. Never embed in HTML.",
                })

            # Check for mixed content
            if is_https and "http://" in body and ("src=" in body_lower or "href=" in body_lower):
                findings.append({
                    "category": "Transport Security",
                    "severity": "medium",
                    "title": "Mixed Content Detected",
                    "description": "HTTPS page loads resources over HTTP, weakening encryption.",
                    "recommendation": "Change all resource URLs to HTTPS or use protocol-relative URLs.",
                })

    except Exception as e:
        logger.error(f"Security scan HTTP check failed for {url}: {e}")
        findings.append({
            "category": "Scan Error",
            "severity": "info",
            "title": "HTTP Scan Incomplete",
            "description": f"Could not complete HTTP analysis: {str(e)[:200]}",
            "recommendation": "Verify the URL is accessible.",
        })

    # 2. SSL Certificate Check
    if is_https and hostname:
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    ssl_data = {
                        "subject": dict(x[0] for x in cert.get("subject", ())),
                        "issuer": dict(x[0] for x in cert.get("issuer", ())),
                        "version": cert.get("version"),
                        "not_before": cert.get("notBefore"),
                        "not_after": cert.get("notAfter"),
                        "serial": cert.get("serialNumber"),
                    }

                    # Check expiry
                    not_after = ssl.cert_time_to_seconds(cert["notAfter"])
                    days_left = (not_after - datetime.now(timezone.utc).timestamp()) / 86400

                    if days_left < 0:
                        findings.append({
                            "category": "SSL/TLS",
                            "severity": "critical",
                            "title": "SSL Certificate Expired",
                            "description": f"Certificate expired {abs(int(days_left))} days ago.",
                            "recommendation": "Renew the SSL certificate immediately.",
                        })
                    elif days_left < 30:
                        findings.append({
                            "category": "SSL/TLS",
                            "severity": "high",
                            "title": "SSL Certificate Expiring Soon",
                            "description": f"Certificate expires in {int(days_left)} days.",
                            "recommendation": "Renew the SSL certificate before expiry.",
                        })

                    ssl_data["days_until_expiry"] = int(days_left)

        except ssl.SSLCertVerificationError as e:
            findings.append({
                "category": "SSL/TLS",
                "severity": "critical",
                "title": "SSL Certificate Invalid",
                "description": f"Certificate verification failed: {str(e)[:200]}",
                "recommendation": "Fix the SSL certificate — may be self-signed, expired, or wrong domain.",
            })
            ssl_data["error"] = str(e)[:200]
        except Exception as e:
            ssl_data["error"] = str(e)[:200]

    # Calculate score — weighted by severity with diminishing impact for low findings
    # Each severity has a per-finding deduction AND a cap (so many low findings don't tank the score)
    severity_config = {
        "critical": {"per": 25, "cap": 50},   # Max 50 pts lost from critical
        "high":     {"per": 15, "cap": 30},   # Max 30 pts lost from high
        "medium":   {"per": 5,  "cap": 20},   # Max 20 pts lost from medium
        "low":      {"per": 1,  "cap": 5},    # Max 5 pts lost from low
        "info":     {"per": 0,  "cap": 0},
    }
    deductions = 0
    for sev, config in severity_config.items():
        count = sum(1 for f in findings if f["severity"] == sev)
        deductions += min(count * config["per"], config["cap"])

    score = max(0, 100 - deductions)

    # Grade thresholds (aligned with industry: A = excellent, F = serious issues)
    if score >= 90: grade = "A+"
    elif score >= 80: grade = "A"
    elif score >= 70: grade = "B"
    elif score >= 60: grade = "C"
    elif score >= 40: grade = "D"
    else: grade = "F"

    return {
        "score": score,
        "grade": grade,
        "findings": findings,
        "total_findings": len(findings),
        "critical_count": sum(1 for f in findings if f["severity"] == "critical"),
        "high_count": sum(1 for f in findings if f["severity"] == "high"),
        "medium_count": sum(1 for f in findings if f["severity"] == "medium"),
        "low_count": sum(1 for f in findings if f["severity"] == "low"),
        "info_count": sum(1 for f in findings if f["severity"] == "info"),
        "headers_data": headers_data,
        "ssl_data": ssl_data,
    }
