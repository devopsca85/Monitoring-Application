"""
Security Report PDF Generator
Generates a comprehensive security report in PDF format.
"""
import io
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.utils import enum_val
from app.models.models import Site
from app.models.security_models import SecurityScan
from app.services.notification_service import send_email_alert

logger = logging.getLogger(__name__)


def _generate_security_html(db: Session) -> str:
    """Build HTML for the security PDF report."""
    sites = db.query(Site).filter(Site.is_active == True).all()
    now = datetime.now(timezone.utc)

    site_reports = []
    total_critical = 0
    total_high = 0
    total_medium = 0

    for site in sites:
        scan = (
            db.query(SecurityScan)
            .filter(SecurityScan.site_id == site.id)
            .order_by(SecurityScan.scanned_at.desc())
            .first()
        )
        if not scan:
            continue

        total_critical += scan.critical_count or 0
        total_high += scan.high_count or 0
        total_medium += scan.medium_count or 0

        findings_html = ""
        for f in (scan.findings or []):
            sev_color = {"critical": "#ef4444", "high": "#f97316", "medium": "#f59e0b", "low": "#3b82f6"}.get(f["severity"], "#94a3b8")
            findings_html += f"""
            <tr>
                <td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;">
                    <span style="background:{sev_color};color:white;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:bold;text-transform:uppercase;">{f['severity']}</span>
                </td>
                <td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;font-size:11px;">{f['category']}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;">
                    <strong style="font-size:11px;">{f['title']}</strong>
                    <div style="font-size:10px;color:#6b7280;">{f['description']}</div>
                </td>
                <td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;font-size:10px;color:#059669;">{f['recommendation']}</td>
            </tr>"""

        grade_color = {"A": "#10b981", "B": "#3b82f6", "C": "#f59e0b", "D": "#f97316", "F": "#ef4444"}.get(scan.grade or "F", "#94a3b8")

        site_reports.append(f"""
        <div style="page-break-inside:avoid;margin-bottom:20px;">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;border-bottom:2px solid #e5e7eb;padding-bottom:8px;">
                <div style="width:36px;height:36px;border-radius:50%;background:{grade_color};color:white;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:16px;">{scan.grade or '?'}</div>
                <div>
                    <div style="font-size:14px;font-weight:bold;">{site.name}</div>
                    <div style="font-size:11px;color:#6b7280;">{site.url} | Score: {scan.score}/100 | Scanned: {scan.scanned_at.strftime('%b %d, %Y %I:%M %p') if scan.scanned_at else 'N/A'}</div>
                </div>
            </div>
            <div style="display:flex;gap:8px;margin-bottom:8px;">
                <span style="background:#fef2f2;color:#ef4444;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:bold;">Critical: {scan.critical_count}</span>
                <span style="background:#fff7ed;color:#f97316;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:bold;">High: {scan.high_count}</span>
                <span style="background:#fffbeb;color:#f59e0b;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:bold;">Medium: {scan.medium_count}</span>
                <span style="background:#eff6ff;color:#3b82f6;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:bold;">Low: {scan.low_count}</span>
            </div>
            {"<table style='width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:6px;'><thead><tr style='background:#f9fafb;'><th style='padding:6px 10px;text-align:left;font-size:10px;font-weight:600;text-transform:uppercase;color:#6b7280;'>Severity</th><th style='padding:6px 10px;text-align:left;font-size:10px;font-weight:600;text-transform:uppercase;color:#6b7280;'>Category</th><th style='padding:6px 10px;text-align:left;font-size:10px;font-weight:600;text-transform:uppercase;color:#6b7280;'>Finding</th><th style='padding:6px 10px;text-align:left;font-size:10px;font-weight:600;text-transform:uppercase;color:#6b7280;'>Recommendation</th></tr></thead><tbody>" + findings_html + "</tbody></table>" if findings_html else "<p style='color:#6b7280;font-size:12px;text-align:center;padding:16px;'>No findings — site passed all checks</p>"}
        </div>""")

    scanned_count = len(site_reports)
    avg_score = 0
    if scanned_count > 0:
        scores = []
        for site in sites:
            scan = db.query(SecurityScan).filter(SecurityScan.site_id == site.id).order_by(SecurityScan.scanned_at.desc()).first()
            if scan:
                scores.append(scan.score)
        avg_score = round(sum(scores) / len(scores)) if scores else 0

    html = f"""
    <html><head><style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 12px; color: #1f2937; margin: 40px; }}
        h1 {{ font-size: 22px; margin: 0; }}
        h2 {{ font-size: 16px; margin: 20px 0 10px; }}
    </style></head><body>
        <div style="border-bottom:3px solid #0f172a;padding-bottom:16px;margin-bottom:20px;">
            <h1>Security Scan Report</h1>
            <p style="color:#6b7280;margin:4px 0 0;">Generated: {now.strftime('%B %d, %Y %I:%M %p')} UTC | {scanned_count} sites scanned</p>
        </div>

        <div style="display:flex;gap:16px;margin-bottom:20px;">
            <div style="flex:1;background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:12px;text-align:center;">
                <div style="font-size:28px;font-weight:bold;color:#3b82f6;">{avg_score}/100</div>
                <div style="font-size:11px;color:#6b7280;">Avg Score</div>
            </div>
            <div style="flex:1;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px;text-align:center;">
                <div style="font-size:28px;font-weight:bold;color:#ef4444;">{total_critical}</div>
                <div style="font-size:11px;color:#6b7280;">Critical</div>
            </div>
            <div style="flex:1;background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:12px;text-align:center;">
                <div style="font-size:28px;font-weight:bold;color:#f97316;">{total_high}</div>
                <div style="font-size:11px;color:#6b7280;">High</div>
            </div>
            <div style="flex:1;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:12px;text-align:center;">
                <div style="font-size:28px;font-weight:bold;color:#f59e0b;">{total_medium}</div>
                <div style="font-size:11px;color:#6b7280;">Medium</div>
            </div>
        </div>

        <h2>Site Details</h2>
        {''.join(site_reports)}

        <div style="margin-top:30px;padding-top:16px;border-top:1px solid #e5e7eb;text-align:center;font-size:10px;color:#9ca3af;">
            Monitoring Application v1.0 — Confidential Security Report
        </div>
    </body></html>"""

    return html


def generate_security_pdf() -> bytes:
    """Generate PDF bytes from the security report."""
    db = SessionLocal()
    try:
        html = _generate_security_html(db)
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html).write_pdf()
            return pdf_bytes
        except ImportError:
            logger.warning("weasyprint not installed — returning HTML as fallback")
            return html.encode("utf-8")
    finally:
        db.close()


async def send_security_report_email():
    """Send the security PDF report to all admin users."""
    db = SessionLocal()
    try:
        from app.models.models import User
        admins = db.query(User).filter(User.is_admin == True, User.is_active == True).all()
        admin_emails = [a.email for a in admins if a.email]

        if not admin_emails:
            logger.warning("Security report: no admin emails")
            return

        html = _generate_security_html(db)
        subject = f"Security Scan Report — {datetime.now(timezone.utc).strftime('%B %d, %Y')}"

        await send_email_alert(admin_emails, subject, html)
        logger.info(f"Security report sent to {len(admin_emails)} admin(s)")
    except Exception as e:
        logger.error(f"Security report failed: {e}", exc_info=True)
    finally:
        db.close()
