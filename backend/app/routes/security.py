"""
Security & Compliance API Routes
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Site, User
from app.models.security_models import SecurityScan, ComplianceFramework, ComplianceControl
from app.routes.auth import get_current_user
from app.services.security_scanner import scan_site_security

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/security", tags=["security"])


# --- Security Scans ---

@router.post("/scan/{site_id}")
async def run_security_scan(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run a DAST security scan on a site."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    logger.info(f"Security scan starting for {site.name} ({site.url})")
    result = await scan_site_security(site.url)

    scan = SecurityScan(
        site_id=site.id,
        score=result["score"],
        grade=result["grade"],
        total_findings=result["total_findings"],
        critical_count=result["critical_count"],
        high_count=result["high_count"],
        medium_count=result["medium_count"],
        low_count=result["low_count"],
        info_count=result["info_count"],
        findings=result["findings"],
        headers_data=result["headers_data"],
        ssl_data=result["ssl_data"],
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    logger.info(f"Security scan complete: {site.name} — Grade {result['grade']} ({result['score']}/100)")

    # Auto-update compliance controls based on scan results
    try:
        from app.services.compliance_mapper import evaluate_compliance_from_scan
        controls_updated = evaluate_compliance_from_scan(db, scan, site.name)
        logger.info(f"Compliance auto-update: {controls_updated} controls updated")
    except Exception as e:
        logger.error(f"Compliance auto-update failed: {e}")

    return {
        "scan_id": scan.id,
        "score": result["score"],
        "grade": result["grade"],
        "total_findings": result["total_findings"],
        "critical": result["critical_count"],
        "high": result["high_count"],
    }


@router.get("/scans/{site_id}")
def get_security_scans(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get security scan history for a site."""
    scans = (
        db.query(SecurityScan)
        .filter(SecurityScan.site_id == site_id)
        .order_by(SecurityScan.scanned_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": s.id,
            "scanned_at": s.scanned_at.isoformat() + "+00:00" if s.scanned_at else None,
            "score": s.score,
            "grade": s.grade,
            "total_findings": s.total_findings,
            "critical_count": s.critical_count,
            "high_count": s.high_count,
            "medium_count": s.medium_count,
            "low_count": s.low_count,
        }
        for s in scans
    ]


@router.get("/scans/{site_id}/latest")
def get_latest_scan(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the most recent scan with full findings."""
    scan = (
        db.query(SecurityScan)
        .filter(SecurityScan.site_id == site_id)
        .order_by(SecurityScan.scanned_at.desc())
        .first()
    )
    if not scan:
        return {"has_scan": False}

    return {
        "has_scan": True,
        "id": scan.id,
        "scanned_at": scan.scanned_at.isoformat() + "+00:00" if scan.scanned_at else None,
        "score": scan.score,
        "grade": scan.grade,
        "total_findings": scan.total_findings,
        "critical_count": scan.critical_count,
        "high_count": scan.high_count,
        "medium_count": scan.medium_count,
        "low_count": scan.low_count,
        "info_count": scan.info_count,
        "findings": scan.findings or [],
        "ssl_data": scan.ssl_data or {},
    }


# --- Security Dashboard (aggregate) ---

@router.get("/dashboard")
def security_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Aggregate security overview across all sites."""
    sites = db.query(Site).filter(Site.is_active == True).all()
    site_scores = []

    for site in sites:
        latest = (
            db.query(SecurityScan)
            .filter(SecurityScan.site_id == site.id)
            .order_by(SecurityScan.scanned_at.desc())
            .first()
        )
        site_scores.append({
            "site_id": site.id,
            "site_name": site.name,
            "site_url": site.url,
            "has_scan": latest is not None,
            "score": latest.score if latest else None,
            "grade": latest.grade if latest else None,
            "critical": latest.critical_count if latest else 0,
            "high": latest.high_count if latest else 0,
            "medium": latest.medium_count if latest else 0,
            "low": latest.low_count if latest else 0,
            "scanned_at": latest.scanned_at.isoformat() + "+00:00" if latest and latest.scanned_at else None,
        })

    scanned = [s for s in site_scores if s["has_scan"]]
    avg_score = round(sum(s["score"] for s in scanned) / len(scanned)) if scanned else 0
    total_critical = sum(s["critical"] for s in scanned)
    total_high = sum(s["high"] for s in scanned)

    return {
        "total_sites": len(sites),
        "scanned_sites": len(scanned),
        "avg_score": avg_score,
        "total_critical": total_critical,
        "total_high": total_high,
        "sites": site_scores,
    }


# --- Compliance Framework ---

class ControlUpdate(BaseModel):
    status: str | None = None
    evidence: str | None = None
    assigned_to: str | None = None
    due_date: str | None = None


@router.get("/compliance/frameworks")
def list_frameworks(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    frameworks = db.query(ComplianceFramework).filter(ComplianceFramework.is_active == True).all()
    result = []
    for f in frameworks:
        controls = f.controls or []
        compliant = sum(1 for c in controls if c.status == "compliant")
        total = len(controls)
        result.append({
            "id": f.id,
            "name": f.name,
            "description": f.description or "",
            "total_controls": total,
            "compliant": compliant,
            "compliance_pct": round(compliant / max(total, 1) * 100, 1),
            "non_compliant": sum(1 for c in controls if c.status == "non_compliant"),
            "in_progress": sum(1 for c in controls if c.status == "in_progress"),
            "not_started": sum(1 for c in controls if c.status == "not_started"),
        })
    return result


@router.get("/compliance/frameworks/{framework_id}")
def get_framework_controls(
    framework_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    f = db.query(ComplianceFramework).filter(ComplianceFramework.id == framework_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Framework not found")

    return {
        "id": f.id,
        "name": f.name,
        "description": f.description or "",
        "controls": [
            {
                "id": c.id,
                "control_id": c.control_id or "",
                "category": c.category or "",
                "title": c.title,
                "description": c.description or "",
                "check_type": c.check_type or "manual",
                "status": c.status or "not_started",
                "evidence": c.evidence or "",
                "assigned_to": c.assigned_to or "",
                "due_date": c.due_date.isoformat() if c.due_date else None,
                "last_reviewed": c.last_reviewed.isoformat() if c.last_reviewed else None,
                "reviewed_by": c.reviewed_by or "",
            }
            for c in (f.controls or [])
        ],
    }


@router.put("/compliance/controls/{control_id}")
def update_control(
    control_id: int,
    data: ControlUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.query(ComplianceControl).filter(ComplianceControl.id == control_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Control not found")

    if data.status is not None:
        c.status = data.status
    if data.evidence is not None:
        c.evidence = data.evidence
    if data.assigned_to is not None:
        c.assigned_to = data.assigned_to
    if data.due_date is not None:
        try:
            c.due_date = datetime.fromisoformat(data.due_date)
        except Exception:
            pass

    c.last_reviewed = datetime.now(timezone.utc)
    c.reviewed_by = user.email
    db.commit()
    return {"status": "Control updated"}


@router.post("/compliance/seed")
def seed_frameworks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Seed default compliance frameworks (SOC 2, GDPR). Admin only."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # SOC 2 Type II controls (simplified)
    soc2_controls = [
        ("CC1.1", "Control Environment", "Demonstrates commitment to integrity and ethical values"),
        ("CC2.1", "Communication", "Internal communication of security policies"),
        ("CC3.1", "Risk Assessment", "Identifies and assesses risks to objectives"),
        ("CC4.1", "Monitoring", "Monitors internal controls and remediates deficiencies"),
        ("CC5.1", "Control Activities", "Selects and develops control activities over technology"),
        ("CC6.1", "Logical Access", "Restricts logical access to information assets"),
        ("CC6.2", "Logical Access", "Authenticates users before granting access"),
        ("CC6.3", "Logical Access", "Manages authorization for data and systems"),
        ("CC6.6", "Logical Access", "Restricts access through network security controls"),
        ("CC6.7", "Logical Access", "Restricts modification of data and software"),
        ("CC6.8", "Logical Access", "Prevents unauthorized or malicious software"),
        ("CC7.1", "System Operations", "Detects and monitors for security events"),
        ("CC7.2", "System Operations", "Monitors for anomalies indicating security incidents"),
        ("CC7.3", "System Operations", "Evaluates and responds to security events"),
        ("CC7.4", "System Operations", "Responds to identified security incidents"),
        ("CC8.1", "Change Management", "Manages changes to infrastructure and software"),
        ("CC9.1", "Risk Mitigation", "Identifies and mitigates risk from business disruptions"),
        ("A1.1", "Availability", "Maintains processing capacity to meet commitments"),
        ("A1.2", "Availability", "Provides for recovery of data and infrastructure"),
        ("A1.3", "Availability", "Tests recovery plan procedures"),
    ]

    # GDPR controls (simplified)
    gdpr_controls = [
        ("Art.5", "Data Principles", "Personal data processed lawfully, fairly, and transparently"),
        ("Art.6", "Lawful Basis", "Processing has a legal basis (consent, contract, etc.)"),
        ("Art.7", "Consent", "Conditions for valid consent documented"),
        ("Art.12", "Transparency", "Information provided to data subjects in clear language"),
        ("Art.13", "Privacy Notice", "Information provided when data is collected"),
        ("Art.15", "Right of Access", "Data subjects can request access to their data"),
        ("Art.17", "Right to Erasure", "Data subjects can request deletion of data"),
        ("Art.20", "Data Portability", "Data subjects can receive their data in portable format"),
        ("Art.25", "Privacy by Design", "Data protection built into processing activities"),
        ("Art.28", "Processors", "Data processing agreements with third parties"),
        ("Art.30", "Records", "Records of processing activities maintained"),
        ("Art.32", "Security", "Appropriate technical and organizational security measures"),
        ("Art.33", "Breach Notification", "72-hour breach notification to supervisory authority"),
        ("Art.34", "Data Subject Notification", "Notification to affected individuals for high-risk breaches"),
        ("Art.35", "DPIA", "Data Protection Impact Assessments for high-risk processing"),
        ("Art.37", "DPO", "Data Protection Officer appointed where required"),
    ]

    existing = db.query(ComplianceFramework).count()
    if existing > 0:
        return {"status": "Frameworks already seeded", "count": existing}

    for name, controls_data, desc in [
        ("SOC 2 Type II", soc2_controls, "Service Organization Control 2 — Trust Services Criteria"),
        ("GDPR", gdpr_controls, "General Data Protection Regulation — EU Data Privacy"),
    ]:
        framework = ComplianceFramework(name=name, description=desc)
        db.add(framework)
        db.flush()
        for ctrl_id, category, title in controls_data:
            db.add(ComplianceControl(
                framework_id=framework.id,
                control_id=ctrl_id,
                category=category,
                title=title,
            ))

    db.commit()
    return {"status": "Frameworks seeded", "frameworks": ["SOC 2 Type II", "GDPR"]}


# --- PDF Reports ---

@router.get("/report/download")
def download_security_report(
    user: User = Depends(get_current_user),
):
    """Download security scan report as PDF."""
    from fastapi.responses import Response
    from app.services.security_report import generate_security_pdf

    pdf_bytes = generate_security_pdf()
    filename = f"security-report-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/report/send")
async def send_security_report(
    user: User = Depends(get_current_user),
):
    """Manually send security report email to all admins."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    from app.services.security_report import send_security_report_email
    await send_security_report_email()
    return {"status": "Security report sent"}
