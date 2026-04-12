"""
Compliance Auto-Mapper
Maps security scan results to compliance framework controls.
After each scan, automatically updates control status based on findings.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.security_models import ComplianceControl, ComplianceFramework, SecurityScan

logger = logging.getLogger(__name__)

# Mapping: control_id → { check_fn(scan_result) → True if compliant, evidence_text }
# Each entry defines what scan conditions satisfy that control.

SOC2_MAPPINGS = {
    "CC6.6": {
        "title": "Restricts access through network security controls",
        "checks": [
            {"finding_category": "Transport Security", "must_not_have": True,
             "evidence_pass": "HTTPS enforced, HSTS header present",
             "evidence_fail": "Missing HTTPS or HSTS — network transport not secured"},
        ],
    },
    "CC6.1": {
        "title": "Restricts logical access to information assets",
        "checks": [
            {"finding_category": "Cookie Security", "must_not_have": True,
             "evidence_pass": "Session cookies secured with HttpOnly, Secure, SameSite flags",
             "evidence_fail": "Cookie security flags missing — session hijacking risk"},
        ],
    },
    "CC6.8": {
        "title": "Prevents unauthorized or malicious software",
        "checks": [
            {"finding_category": "XSS Protection", "must_not_have": True,
             "evidence_pass": "Content-Security-Policy header configured — XSS protection active",
             "evidence_fail": "Missing CSP header — vulnerable to cross-site scripting"},
        ],
    },
    "CC7.1": {
        "title": "Detects and monitors for security events",
        "checks": [
            {"finding_category": "Information Disclosure", "must_not_have": True,
             "evidence_pass": "Server version headers hidden — reduced attack surface",
             "evidence_fail": "Server/technology version exposed — increases attack surface"},
        ],
    },
    "CC6.7": {
        "title": "Restricts modification of data and software",
        "checks": [
            {"finding_category": "Clickjacking", "must_not_have": True,
             "evidence_pass": "X-Frame-Options header set — clickjacking protection active",
             "evidence_fail": "Missing X-Frame-Options — site can be framed"},
            {"finding_category": "MIME Sniffing", "must_not_have": True,
             "evidence_pass": "X-Content-Type-Options: nosniff configured",
             "evidence_fail": "Missing X-Content-Type-Options header"},
        ],
    },
}

GDPR_MAPPINGS = {
    "Art.32": {
        "title": "Appropriate technical and organizational security measures",
        "checks": [
            {"finding_category": "Transport Security", "must_not_have": True,
             "evidence_pass": "HTTPS/TLS encryption enforced for data in transit",
             "evidence_fail": "Data transmitted without encryption — HTTPS/HSTS missing"},
            {"finding_category": "SSL/TLS", "must_not_have": True,
             "evidence_pass": "Valid SSL certificate with no expiry issues",
             "evidence_fail": "SSL certificate issues detected"},
        ],
    },
    "Art.25": {
        "title": "Privacy by Design",
        "checks": [
            {"finding_category": "Privacy", "must_not_have": True,
             "evidence_pass": "Referrer-Policy and Permissions-Policy headers configured",
             "evidence_fail": "Missing privacy headers — user data may leak to third parties"},
            {"finding_category": "Cookie Security", "must_not_have": True,
             "evidence_pass": "Cookies configured with SameSite attribute — CSRF protection",
             "evidence_fail": "Cookies missing SameSite — cross-site request forgery risk"},
        ],
    },
    "Art.5": {
        "title": "Personal data processed lawfully, fairly, and transparently",
        "checks": [
            {"finding_category": "Sensitive Data", "must_not_have": True,
             "evidence_pass": "No sensitive data (API keys, secrets) exposed in page source",
             "evidence_fail": "Potential sensitive data exposed in HTML — violates data minimization"},
        ],
    },
}


def evaluate_compliance_from_scan(db: Session, scan: SecurityScan, site_name: str):
    """After a security scan, auto-update compliance controls that map to scan findings."""
    findings = scan.findings or []
    finding_categories = {f["category"] for f in findings}

    # Process each framework
    frameworks = db.query(ComplianceFramework).filter(ComplianceFramework.is_active == True).all()

    updated = 0
    for fw in frameworks:
        mappings = {}
        if "SOC" in fw.name.upper():
            mappings = SOC2_MAPPINGS
        elif "GDPR" in fw.name.upper():
            mappings = GDPR_MAPPINGS
        else:
            continue

        controls = db.query(ComplianceControl).filter(ComplianceControl.framework_id == fw.id).all()
        control_map = {c.control_id: c for c in controls}

        for ctrl_id, mapping in mappings.items():
            control = control_map.get(ctrl_id)
            if not control:
                continue

            # Skip if manually set to N/A
            if control.status == "not_applicable":
                continue

            # Evaluate all checks for this control
            all_pass = True
            evidence_parts = []

            for check in mapping["checks"]:
                category = check["finding_category"]
                has_finding = category in finding_categories

                if check["must_not_have"]:
                    # Control passes if this category has NO findings
                    if has_finding:
                        all_pass = False
                        evidence_parts.append(f"FAIL: {check['evidence_fail']}")
                    else:
                        evidence_parts.append(f"PASS: {check['evidence_pass']}")

            # Update control
            new_status = "compliant" if all_pass else "non_compliant"
            evidence_text = (
                f"[Auto-assessed from security scan of {site_name} — "
                f"{scan.scanned_at.strftime('%b %d, %Y') if scan.scanned_at else 'N/A'}]\n"
                + "\n".join(evidence_parts)
            )

            # Only auto-update if it was not_started, in_progress, or already auto-assessed
            if control.status in ("not_started", "in_progress") or (control.evidence and "[Auto-assessed" in control.evidence):
                old_status = control.status
                control.status = new_status
                control.evidence = evidence_text
                control.check_type = "automated"
                control.last_reviewed = datetime.now(timezone.utc)
                control.reviewed_by = "security-scanner"
                updated += 1

                if old_status != new_status:
                    logger.info(f"Compliance {fw.name} {ctrl_id}: {old_status} → {new_status}")

    if updated:
        db.commit()
        logger.info(f"Compliance auto-update: {updated} controls updated from scan")

    return updated
