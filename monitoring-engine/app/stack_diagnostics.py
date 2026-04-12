"""
Multi-Stack Diagnostics
Detects framework-specific errors and issues based on the configured tech stack.
Supports: ASP.NET, PHP, Node.js, React, Angular, Vue, Python, Java, Ruby, WordPress, Drupal.
"""
import logging

logger = logging.getLogger(__name__)

# Stack-specific error patterns: { stack: [(pattern, category, diagnosis, recommendation)] }
STACK_PATTERNS = {
    "asp_net": [
        ("server error in", "aspnet_error", "ASP.NET server error", "Check Application Event Log and web.config"),
        ("runtime error", "aspnet_runtime", "ASP.NET runtime error", "Review stack trace, check recent deployments"),
        ("compilation error", "aspnet_compile", "ASP.NET compilation error", "Check code syntax, verify DLLs deployed"),
        ("parser error", "aspnet_parser", "ASP.NET parser error", "Review ASPX/CSHTML markup syntax"),
        ("viewstate", "aspnet_viewstate", "ViewState validation failure", "Check machineKey config across servers"),
        ("request validation", "aspnet_validation", "ASP.NET request validation error", "Review input handling, check ValidateRequest"),
        ("yellowscreen", "aspnet_ysod", "Yellow Screen of Death", "Disable customErrors temporarily to see full error"),
    ],
    "asp_net_core": [
        ("an unhandled exception occurred", "dotnet_unhandled", ".NET unhandled exception", "Check application logs, review exception middleware"),
        ("kestrel", "dotnet_kestrel", "Kestrel server error", "Check Kestrel configuration and port bindings"),
        ("middleware", "dotnet_middleware", "Middleware pipeline error", "Review Startup.cs middleware order"),
        ("dependency injection", "dotnet_di", "DI container error", "Check service registration in Program.cs"),
    ],
    "php": [
        ("fatal error", "php_fatal", "PHP fatal error", "Check PHP error logs, review code at the line indicated"),
        ("parse error", "php_parse", "PHP parse/syntax error", "Fix syntax error in PHP file"),
        ("warning:", "php_warning", "PHP warning", "Review the warning — may indicate deprecated function or missing file"),
        ("notice:", "php_notice", "PHP notice", "Minor issue — undefined variable or index"),
        ("uncaught exception", "php_exception", "PHP uncaught exception", "Add try/catch handling or fix the root cause"),
        ("allowed memory size", "php_memory", "PHP memory limit exceeded", "Increase memory_limit in php.ini"),
        ("max execution time", "php_timeout", "PHP execution timeout", "Increase max_execution_time or optimize the script"),
        ("mysql_connect", "php_mysql", "PHP MySQL connection error", "Check database credentials and server availability"),
        ("mysqli", "php_mysqli", "PHP MySQLi error", "Check database connection string"),
        ("pdo", "php_pdo", "PHP PDO database error", "Verify DSN, username, and password"),
    ],
    "nodejs": [
        ("cannot find module", "node_module", "Node.js missing module", "Run npm install, check package.json dependencies"),
        ("econnrefused", "node_connrefused", "Node.js connection refused", "Backend service or database is not running"),
        ("eaddrinuse", "node_port", "Node.js port already in use", "Another process is using the port. Kill it or change port"),
        ("unhandledrejection", "node_promise", "Unhandled Promise rejection", "Add .catch() to async operations"),
        ("referenceerror", "node_reference", "Node.js ReferenceError", "Undefined variable — check code"),
        ("typeerror", "node_type", "Node.js TypeError", "Type mismatch — null/undefined access"),
        ("syntaxerror", "node_syntax", "Node.js SyntaxError", "Invalid JavaScript syntax"),
        ("heap out of memory", "node_memory", "Node.js out of memory", "Increase --max-old-space-size or fix memory leaks"),
        ("express", "node_express", "Express.js error", "Check Express middleware and route handlers"),
    ],
    "react": [
        ("react-dom", "react_error", "React rendering error", "Check component tree for errors"),
        ("minified react error", "react_minified", "React production error", "Check browser console for full error"),
        ("hydration", "react_hydration", "React hydration mismatch", "Server/client HTML mismatch — check SSR"),
        ("chunk load", "react_chunk", "React chunk loading failed", "Clear cache, check CDN/build artifacts"),
        ("loading chunk", "react_lazy", "React lazy loading failure", "Check network, code splitting config"),
        ("cannot read prop", "react_null", "React null reference error", "Component accessing undefined prop or state"),
    ],
    "angular": [
        ("angularjs", "angular_error", "Angular error", "Check Angular error handler and console"),
        ("ng-", "angular_directive", "Angular directive error", "Check template syntax and component bindings"),
        ("zone.js", "angular_zone", "Angular Zone.js error", "Async operation issue — check change detection"),
        ("nullinjectorerror", "angular_di", "Angular DI error", "Missing provider — check module imports"),
    ],
    "vue": [
        ("vue warn", "vue_warn", "Vue.js warning", "Check component props, data, and template"),
        ("[vue error]", "vue_error", "Vue.js error", "Review component lifecycle and error boundaries"),
    ],
    "python": [
        ("traceback", "python_traceback", "Python traceback", "Check the stack trace for the error location"),
        ("internal server error", "python_500", "Python 500 error", "Check WSGI/ASGI server logs"),
        ("importerror", "python_import", "Python ImportError", "Missing package — run pip install"),
        ("modulenotfounderror", "python_module", "Python module not found", "Install the missing module"),
        ("django", "python_django", "Django error", "Check Django error page, settings.py, urls.py"),
        ("flask", "python_flask", "Flask error", "Check Flask app routes and error handlers"),
        ("fastapi", "python_fastapi", "FastAPI error", "Check endpoint handlers and Pydantic models"),
    ],
    "java": [
        ("java.lang", "java_error", "Java exception", "Check Java stack trace and application logs"),
        ("nullpointerexception", "java_npe", "Java NullPointerException", "Null reference — check object initialization"),
        ("classnotfound", "java_class", "Java ClassNotFoundException", "Missing class/JAR — check classpath"),
        ("tomcat", "java_tomcat", "Tomcat error", "Check Tomcat logs and web.xml configuration"),
        ("spring", "java_spring", "Spring Framework error", "Check Spring configuration and bean definitions"),
        ("outofmemoryerror", "java_memory", "Java OutOfMemoryError", "Increase JVM heap size (-Xmx)"),
    ],
    "ruby": [
        ("actioncontroller", "ruby_rails", "Ruby on Rails error", "Check Rails logs and routes"),
        ("activerecord", "ruby_db", "ActiveRecord database error", "Check database connection and migrations"),
        ("nomethoderror", "ruby_nomethod", "Ruby NoMethodError", "Calling undefined method — check code"),
        ("routing error", "ruby_routing", "Rails routing error", "Check config/routes.rb"),
    ],
    "wordpress": [
        ("wp-content", "wp_error", "WordPress error", "Check WordPress debug log (wp-content/debug.log)"),
        ("wp-admin", "wp_admin", "WordPress admin error", "Check plugins and theme compatibility"),
        ("database error", "wp_db", "WordPress database error", "Check wp-config.php database credentials"),
        ("white screen", "wp_wsod", "WordPress White Screen of Death", "Enable WP_DEBUG in wp-config.php"),
        ("plugin", "wp_plugin", "WordPress plugin error", "Deactivate recent plugins to isolate the issue"),
    ],
    "drupal": [
        ("drupal", "drupal_error", "Drupal error", "Check Drupal watchdog logs"),
        ("twig", "drupal_twig", "Drupal Twig template error", "Check template syntax and variables"),
    ],
}

# Patterns common to ALL stacks
UNIVERSAL_PATTERNS = [
    ("502 bad gateway", "proxy_502", "Reverse proxy error (502)", "Backend app crashed or timed out. Check app process."),
    ("504 gateway timeout", "proxy_504", "Gateway timeout (504)", "Backend took too long. Check DB queries and external APIs."),
    ("connection refused", "conn_refused", "Connection refused", "Backend service is not running or wrong port."),
    ("connection timed out", "conn_timeout", "Connection timed out", "Network issue or backend overloaded."),
    ("ssl", "ssl_error", "SSL/TLS error", "Check certificate validity, configuration, and chain."),
    ("cors", "cors_error", "CORS policy error", "Check Access-Control-Allow-Origin headers."),
    ("rate limit", "rate_limit", "Rate limited", "Too many requests. Check rate limiting config."),
    ("cloudflare", "cdn_cloudflare", "Cloudflare error", "Check Cloudflare dashboard for origin server issues."),
    ("nginx", "nginx_error", "Nginx error", "Check Nginx error logs and upstream configuration."),
    ("apache", "apache_error", "Apache error", "Check Apache error logs and .htaccess configuration."),
]


async def analyze_stack_diagnostics(page, tech_stack: str, response_time_ms: float) -> dict:
    """Analyze page for stack-specific errors.

    Args:
        page: Playwright page object
        tech_stack: e.g. "php", "nodejs", "react"
        response_time_ms: total response time

    Returns:
        dict with issues list
    """
    result = {"has_issues": False, "issues": [], "stack": tech_stack}

    try:
        page_html = await page.content()
        page_lower = page_html.lower()
    except Exception as e:
        logger.warning(f"Stack diagnostics page scan failed: {e}")
        return result

    issues = []

    # Check stack-specific patterns
    stack_patterns = STACK_PATTERNS.get(tech_stack, [])
    for pattern, category, diagnosis, recommendation in stack_patterns:
        if pattern in page_lower:
            # Extract context
            detail = ""
            try:
                body = await page.inner_text("body")
                for line in body.split("\n"):
                    if pattern in line.strip().lower() and 10 < len(line.strip()) < 500:
                        detail = line.strip()[:200]
                        break
            except Exception:
                pass

            issues.append({
                "category": category,
                "severity": "critical" if "error" in category or "fatal" in category or "memory" in category else "warning",
                "diagnosis": f"{diagnosis}" + (f" — {detail}" if detail else ""),
                "recommendation": recommendation,
                "stack": tech_stack,
            })
            break  # One match per pattern group

    # Check universal patterns (all stacks)
    for pattern, category, diagnosis, recommendation in UNIVERSAL_PATTERNS:
        if pattern in page_lower:
            if not any(i["category"] == category for i in issues):
                issues.append({
                    "category": category,
                    "severity": "critical",
                    "diagnosis": diagnosis,
                    "recommendation": recommendation,
                    "stack": "universal",
                })

    if issues:
        result["has_issues"] = True
        result["issues"] = issues
        logger.info(f"Stack diagnostics ({tech_stack}): {len(issues)} issue(s) found")

    return result
