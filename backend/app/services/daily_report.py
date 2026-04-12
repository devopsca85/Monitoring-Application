"""
Daily Performance Report
Generates and sends a summary email at 9:00 AM CST covering the previous day.
"""
import logging
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.utils import enum_val as _ev

from app.core.database import SessionLocal
from app.models.models import Alert, AlertStatus, MonitoringResult, Site
from app.services.notification_service import send_email_alert, send_teams_alert

logger = logging.getLogger(__name__)

CST = timezone(timedelta(hours=-6))  # Central Standard Time (UTC-6)
CDT = timezone(timedelta(hours=-5))  # Central Daylight Time (UTC-5)


def _get_cst_now():
    """Get current time in US Central (approximate — doesn't handle DST boundary)."""
    utc_now = datetime.now(timezone.utc)
    # Simple DST: March second Sunday to November first Sunday
    year = utc_now.year
    march_second_sun = datetime(year, 3, 8, 2, tzinfo=timezone.utc)
    while march_second_sun.weekday() != 6:
        march_second_sun += timedelta(days=1)
    nov_first_sun = datetime(year, 11, 1, 2, tzinfo=timezone.utc)
    while nov_first_sun.weekday() != 6:
        nov_first_sun += timedelta(days=1)
    if march_second_sun <= utc_now < nov_first_sun:
        return utc_now.astimezone(CDT)
    return utc_now.astimezone(CST)


def _svg_pie_chart(slices, size=160):
    """Generate an inline SVG pie chart. slices = [(value, color, label), ...]"""
    total = sum(s[0] for s in slices)
    if total == 0:
        return ""

    svg_parts = [f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">']
    cx, cy, r = size // 2, size // 2, size // 2 - 5
    start_angle = -90
    for value, color, label in slices:
        if value == 0:
            continue
        pct = value / total
        angle = pct * 360
        end_angle = start_angle + angle
        large = 1 if angle > 180 else 0
        x1 = cx + r * math.cos(math.radians(start_angle))
        y1 = cy + r * math.sin(math.radians(start_angle))
        x2 = cx + r * math.cos(math.radians(end_angle))
        y2 = cy + r * math.sin(math.radians(end_angle))
        if pct >= 0.999:
            svg_parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')
        else:
            svg_parts.append(
                f'<path d="M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {large},1 {x2:.1f},{y2:.1f} Z" fill="{color}"/>'
            )
        start_angle = end_angle

    svg_parts.append("</svg>")
    return "".join(svg_parts)


def _legend_html(slices):
    """Generate legend items for the pie chart."""
    total = sum(s[0] for s in slices)
    items = []
    for value, color, label in slices:
        pct = round(value / max(total, 1) * 100)
        items.append(
            f'<span style="display:inline-flex;align-items:center;gap:6px;margin-right:16px;">'
            f'<span style="width:10px;height:10px;border-radius:50%;background:{color};display:inline-block;"></span>'
            f'{label}: <strong>{value}</strong> ({pct}%)</span>'
        )
    return " ".join(items)


def generate_daily_report(db: Session) -> dict:
    """Generate daily report data for the previous day."""
    now_utc = datetime.now(timezone.utc)
    yesterday_start = (now_utc - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = yesterday_start + timedelta(days=1)

    sites = db.query(Site).filter(Site.is_active == True).all()
    if not sites:
        return {"has_data": False}

    total_sites = len(sites)
    site_reports = []

    all_checks = 0
    all_ok = 0
    all_failures = 0
    all_slow = 0
    all_response_times = []

    for site in sites:
        results = (
            db.query(MonitoringResult)
            .filter(
                MonitoringResult.site_id == site.id,
                MonitoringResult.checked_at >= yesterday_start,
                MonitoringResult.checked_at < yesterday_end,
            )
            .order_by(MonitoringResult.checked_at.asc())
            .all()
        )

        if not results:
            continue

        threshold = site.slow_threshold_ms or 10000
        checks = len(results)
        ok = sum(1 for r in results if _ev(r.status) == "ok")
        failures = sum(1 for r in results if _ev(r.status) != "ok")
        slow = sum(1 for r in results if (r.response_time_ms or 0) > threshold)
        response_times = [r.response_time_ms or 0 for r in results if r.response_time_ms]
        avg_rt = round(sum(response_times) / len(response_times)) if response_times else 0
        max_rt = round(max(response_times)) if response_times else 0
        min_rt = round(min(response_times)) if response_times else 0
        uptime_pct = round(ok / max(checks, 1) * 100, 1)

        # Collect error messages
        errors = []
        for r in results:
            if _ev(r.status) != "ok" and r.error_message:
                errors.append({
                    "time": r.checked_at.strftime("%I:%M %p") if r.checked_at else "",
                    "message": (r.error_message or "")[:150],
                    "status": (r.status.value if hasattr(r.status, 'value') else str(r.status)) if r.status else "critical",
                })

        all_checks += checks
        all_ok += ok
        all_failures += failures
        all_slow += slow
        all_response_times.extend(response_times)

        report = {
            "site_name": site.name,
            "site_url": site.url,
            "checks": checks,
            "ok": ok,
            "failures": failures,
            "slow": slow,
            "uptime_pct": uptime_pct,
            "avg_response_ms": avg_rt,
            "max_response_ms": max_rt,
            "min_response_ms": min_rt,
            "errors": errors[:5],  # Top 5 errors
            "has_issues": failures > 0 or slow > 0,
        }
        site_reports.append(report)

    # Sort: issues first, then by failure count
    site_reports.sort(key=lambda x: (-x["failures"], -x["slow"], x["site_name"]))

    # Alerts from yesterday
    alerts = (
        db.query(Alert)
        .filter(Alert.created_at >= yesterday_start, Alert.created_at < yesterday_end, Alert.false_positive == False)
        .order_by(Alert.created_at.desc())
        .all()
    )

    alert_summary = {
        "total": len(alerts),
        "critical": sum(1 for a in alerts if _ev(a.alert_type) == "critical"),
        "warning": sum(1 for a in alerts if _ev(a.alert_type) == "warning"),
        "resolved": sum(1 for a in alerts if a.resolved),
        "unresolved": sum(1 for a in alerts if not a.resolved),
    }

    overall_avg_rt = round(sum(all_response_times) / len(all_response_times)) if all_response_times else 0

    return {
        "has_data": True,
        "date": (now_utc - timedelta(days=1)).strftime("%B %d, %Y"),
        "total_sites": total_sites,
        "total_checks": all_checks,
        "total_ok": all_ok,
        "total_failures": all_failures,
        "total_slow": all_slow,
        "overall_uptime_pct": round(all_ok / max(all_checks, 1) * 100, 1),
        "overall_avg_response_ms": overall_avg_rt,
        "sites": site_reports,
        "alerts": alert_summary,
    }


def build_report_email(data: dict) -> str:
    """Build an HTML email from report data with inline SVG charts."""
    if not data.get("has_data"):
        return "<p>No monitoring data available for the reporting period.</p>"

    # Status pie chart
    sites_with_issues = sum(1 for s in data["sites"] if s["has_issues"])
    sites_healthy = data["total_sites"] - sites_with_issues
    status_pie = _svg_pie_chart([
        (sites_healthy, "#38a169", "Healthy"),
        (sites_with_issues, "#e53e3e", "Issues"),
    ])
    status_legend = _legend_html([
        (sites_healthy, "#38a169", "Healthy"),
        (sites_with_issues, "#e53e3e", "Issues"),
    ])

    # Check results pie
    results_pie = _svg_pie_chart([
        (data["total_ok"], "#38a169", "OK"),
        (data["total_failures"], "#e53e3e", "Failed"),
        (data["total_slow"], "#dd6b20", "Slow"),
    ])
    results_legend = _legend_html([
        (data["total_ok"], "#38a169", "OK"),
        (data["total_failures"], "#e53e3e", "Failed"),
        (data["total_slow"], "#dd6b20", "Slow"),
    ])

    # Alert pie
    alerts = data["alerts"]
    alert_pie = _svg_pie_chart([
        (alerts["critical"], "#e53e3e", "Critical"),
        (alerts["warning"], "#dd6b20", "Warning"),
    ]) if alerts["total"] > 0 else ""
    alert_legend = _legend_html([
        (alerts["critical"], "#e53e3e", "Critical"),
        (alerts["warning"], "#dd6b20", "Warning"),
    ]) if alerts["total"] > 0 else ""

    # Site rows
    site_rows = ""
    for s in data["sites"]:
        bg = "#fff5f5" if s["failures"] > 0 else ("#fffaf0" if s["slow"] > 0 else "#ffffff")
        status_color = "#e53e3e" if s["failures"] > 0 else ("#dd6b20" if s["slow"] > 0 else "#38a169")
        status_text = "Issues" if s["failures"] > 0 else ("Slow" if s["slow"] > 0 else "Healthy")

        error_rows = ""
        for e in s["errors"]:
            error_rows += f'<div style="font-size:11px;color:#718096;padding:2px 0;">&#8226; {e["time"]} — {e["message"]}</div>'

        site_rows += f"""
        <tr style="background:{bg};">
            <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;">
                <strong style="color:#1f2121;">{s["site_name"]}</strong>
                <div style="font-size:11px;color:#718096;">{s["site_url"]}</div>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;text-align:center;">
                <span style="color:{status_color};font-weight:700;">{status_text}</span>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;text-align:center;font-weight:600;">{s["uptime_pct"]}%</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;text-align:center;">{s["avg_response_ms"]}ms</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;text-align:center;">{s["checks"]}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;text-align:center;color:#e53e3e;font-weight:600;">{s["failures"]}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;text-align:center;color:#dd6b20;">{s["slow"]}</td>
        </tr>
        {"<tr><td colspan='7' style='padding:4px 12px 10px;border-bottom:1px solid #e2e8f0;'>" + error_rows + "</td></tr>" if error_rows else ""}
        """

    html = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:800px;margin:0 auto;background:#ffffff;">
        <!-- Header -->
        <div style="background:linear-gradient(135deg,#001e3f,#003366);color:white;padding:24px 32px;border-radius:8px 8px 0 0;">
            <h1 style="margin:0;font-size:20px;font-weight:600;">Daily Monitoring Report</h1>
            <p style="margin:6px 0 0;opacity:0.85;font-size:14px;">{data["date"]} | {data["total_sites"]} Sites Monitored</p>
        </div>

        <!-- Summary Cards -->
        <div style="padding:20px 32px;background:#f7fafc;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td style="padding:8px;text-align:center;background:white;border-radius:8px;border:1px solid #e2e8f0;">
                        <div style="font-size:28px;font-weight:700;color:#007aff;">{data["total_checks"]}</div>
                        <div style="font-size:11px;color:#718096;">Total Checks</div>
                    </td>
                    <td style="padding:8px;text-align:center;background:white;border-radius:8px;border:1px solid #e2e8f0;">
                        <div style="font-size:28px;font-weight:700;color:#38a169;">{data["overall_uptime_pct"]}%</div>
                        <div style="font-size:11px;color:#718096;">Uptime</div>
                    </td>
                    <td style="padding:8px;text-align:center;background:white;border-radius:8px;border:1px solid #e2e8f0;">
                        <div style="font-size:28px;font-weight:700;color:#e53e3e;">{data["total_failures"]}</div>
                        <div style="font-size:11px;color:#718096;">Failures</div>
                    </td>
                    <td style="padding:8px;text-align:center;background:white;border-radius:8px;border:1px solid #e2e8f0;">
                        <div style="font-size:28px;font-weight:700;color:#dd6b20;">{data["total_slow"]}</div>
                        <div style="font-size:11px;color:#718096;">Slow</div>
                    </td>
                    <td style="padding:8px;text-align:center;background:white;border-radius:8px;border:1px solid #e2e8f0;">
                        <div style="font-size:28px;font-weight:700;color:#007aff;">{data["overall_avg_response_ms"]}ms</div>
                        <div style="font-size:11px;color:#718096;">Avg Response</div>
                    </td>
                </tr>
            </table>
        </div>

        <!-- Charts -->
        <div style="padding:20px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td style="text-align:center;padding:12px;vertical-align:top;">
                        <h3 style="font-size:14px;margin:0 0 10px;color:#1f2121;">Site Health</h3>
                        {status_pie}
                        <div style="margin-top:8px;font-size:12px;">{status_legend}</div>
                    </td>
                    <td style="text-align:center;padding:12px;vertical-align:top;">
                        <h3 style="font-size:14px;margin:0 0 10px;color:#1f2121;">Check Results</h3>
                        {results_pie}
                        <div style="margin-top:8px;font-size:12px;">{results_legend}</div>
                    </td>
                    {"<td style='text-align:center;padding:12px;vertical-align:top;'><h3 style='font-size:14px;margin:0 0 10px;color:#1f2121;'>Alerts (" + str(alerts['total']) + ")</h3>" + alert_pie + "<div style='margin-top:8px;font-size:12px;'>" + alert_legend + "</div><div style='font-size:11px;color:#718096;margin-top:4px;'>Resolved: " + str(alerts['resolved']) + " | Open: " + str(alerts['unresolved']) + "</div></td>" if alerts['total'] > 0 else ""}
                </tr>
            </table>
        </div>

        <!-- Site Details Table -->
        <div style="padding:0 32px 20px;">
            <h3 style="font-size:16px;margin:0 0 12px;color:#1f2121;">Site Performance Details</h3>
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
                <thead>
                    <tr style="background:#edf2f7;">
                        <th style="padding:10px 12px;text-align:left;font-size:11px;font-weight:600;color:#718096;text-transform:uppercase;">Site</th>
                        <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:600;color:#718096;text-transform:uppercase;">Status</th>
                        <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:600;color:#718096;text-transform:uppercase;">Uptime</th>
                        <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:600;color:#718096;text-transform:uppercase;">Avg Response</th>
                        <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:600;color:#718096;text-transform:uppercase;">Checks</th>
                        <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:600;color:#718096;text-transform:uppercase;">Failures</th>
                        <th style="padding:10px 12px;text-align:center;font-size:11px;font-weight:600;color:#718096;text-transform:uppercase;">Slow</th>
                    </tr>
                </thead>
                <tbody>
                    {site_rows}
                </tbody>
            </table>
        </div>

        <!-- Footer -->
        <div style="padding:16px 32px;background:#f7fafc;border-radius:0 0 8px 8px;text-align:center;font-size:11px;color:#a0aec0;">
            Generated at {_get_cst_now().strftime("%I:%M %p CST")} | Monitoring Application v1.0
        </div>
    </div>
    """
    return html


async def send_daily_report():
    """Generate and send the daily report to all admin users."""
    db = SessionLocal()
    try:
        from app.models.models import User
        admins = db.query(User).filter(User.is_admin == True, User.is_active == True).all()
        admin_emails = [a.email for a in admins if a.email]

        if not admin_emails:
            logger.warning("Daily report: no admin emails found")
            return

        data = generate_daily_report(db)
        if not data.get("has_data"):
            logger.info("Daily report: no data for yesterday")
            return

        html = build_report_email(data)
        subject = f"Daily Monitoring Report — {data['date']} | {data['overall_uptime_pct']}% Uptime"

        await send_email_alert(admin_emails, subject, html)
        logger.info(f"Daily report sent to {len(admin_emails)} admin(s)")

        # Also send summary to Teams
        teams_msg = (
            f"**Daily Report — {data['date']}**\n\n"
            f"Sites: {data['total_sites']} | Checks: {data['total_checks']} | "
            f"Uptime: {data['overall_uptime_pct']}%\n"
            f"Failures: {data['total_failures']} | Slow: {data['total_slow']} | "
            f"Avg Response: {data['overall_avg_response_ms']}ms\n"
            f"Alerts: {data['alerts']['total']} (Critical: {data['alerts']['critical']}, Warning: {data['alerts']['warning']})"
        )
        await send_teams_alert(f"Daily Report — {data['date']}", teams_msg, "007AFF")

    except Exception as e:
        logger.error(f"Daily report failed: {e}", exc_info=True)
    finally:
        db.close()
