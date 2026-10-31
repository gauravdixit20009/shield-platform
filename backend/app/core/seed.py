"""
SHIELD Platform — Production Auto-Seed Module
Ensures authorized clearance profiles (DGP, SP, SI), initial active cases, and
statutory FIR/NCR sample records always exist on boot.
"""
from datetime import datetime, timezone
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.officer import Officer, OfficerRank, Department
from app.models.case import Case, CasePriority, CaseStatus, CrimeCategory, Suspect, Evidence, EvidenceType
from app.auth.auth_service import AuthService
from app.models.audit import AuditLog, AuditAction
from app.utils.logger import logger

DEV_TOTP_SECRET = "JBSWY3DPEHPK3PXP"


async def auto_seed_db():
    """
    Idempotent database seeding called during FastAPI startup.
    Ensures DGP-INDIA-01, IPS-MH-2024-001, and SI-MH-2026-089 exist with Password@123.
    """
    async with AsyncSessionLocal() as db:
        hashed_pw = AuthService.hash_password("Password@123")

        # 1. Verify or create DGP Officer
        res_dgp = await db.execute(select(Officer).where(Officer.badge_number == "DGP-INDIA-01"))
        dgp = res_dgp.scalar_one_or_none()

        if not dgp:
            logger.info("Seeding DGP-INDIA-01 clearance account...")
            dgp = Officer(
                badge_number="DGP-INDIA-01",
                full_name="Rajeshwar Sharma, IPS",
                rank=OfficerRank.DGP,
                department=Department.STATE_POLICE,
                state="Maharashtra",
                district="Mumbai",
                station_code="HQ-01",
                email="dgp@shield.gov.in",
                phone="+919876543210",
                hashed_password=hashed_pw,
                totp_secret=DEV_TOTP_SECRET,
                is_mfa_enabled=True,
                is_active=True,
                is_suspended=False,
                threat_level="LOW",
                threat_score=5,
            )
            db.add(dgp)
            await db.flush()
        else:
            # Ensure password and status are clean
            if not AuthService.verify_password("Password@123", dgp.hashed_password):
                dgp.hashed_password = hashed_pw
            dgp.is_active = True
            dgp.is_suspended = False
            dgp.totp_secret = DEV_TOTP_SECRET
            await db.flush()

        # 2. Verify or create SP Officer
        res_sp = await db.execute(select(Officer).where(Officer.badge_number == "IPS-MH-2024-001"))
        sp = res_sp.scalar_one_or_none()

        if not sp:
            logger.info("Seeding IPS-MH-2024-001 clearance account...")
            sp = Officer(
                badge_number="IPS-MH-2024-001",
                full_name="Vikramaditya Roy, IPS",
                rank=OfficerRank.IPS,
                department=Department.STATE_POLICE,
                state="Maharashtra",
                district="Mumbai",
                station_code="CPS-02",
                email="vikram.ips@shield.gov.in",
                phone="+919876543211",
                hashed_password=hashed_pw,
                totp_secret=DEV_TOTP_SECRET,
                is_mfa_enabled=True,
                is_active=True,
                is_suspended=False,
                is_on_duty=True,
                threat_level="LOW",
                threat_score=10,
                superior_officer_id=dgp.id,
            )
            db.add(sp)
            await db.flush()
        else:
            if not AuthService.verify_password("Password@123", sp.hashed_password):
                sp.hashed_password = hashed_pw
            sp.is_active = True
            sp.is_suspended = False
            sp.totp_secret = DEV_TOTP_SECRET
            await db.flush()

        # 3. Verify or create Sub-Inspector (SI)
        res_si = await db.execute(select(Officer).where(Officer.badge_number == "SI-MH-2026-089"))
        si = res_si.scalar_one_or_none()

        if not si:
            logger.info("Seeding SI-MH-2026-089 clearance account...")
            si = Officer(
                badge_number="SI-MH-2026-089",
                full_name="Amit Verma, Sub-Inspector",
                rank=OfficerRank.SI,
                department=Department.STATE_POLICE,
                state="Maharashtra",
                district="Mumbai",
                station_code="CPS-02",
                email="amit.si@shield.gov.in",
                phone="+919876543212",
                hashed_password=hashed_pw,
                totp_secret=DEV_TOTP_SECRET,
                is_mfa_enabled=True,
                is_active=True,
                is_suspended=False,
                is_on_duty=True,
                threat_level="LOW",
                threat_score=5,
                superior_officer_id=sp.id,
            )
            db.add(si)
            await db.flush()
        else:
            if not AuthService.verify_password("Password@123", si.hashed_password):
                si.hashed_password = hashed_pw
            si.is_active = True
            si.is_suspended = False
            si.totp_secret = DEV_TOTP_SECRET
            await db.flush()

        # 4. Check if cases exist; if not, seed initial cases
        res_cases = await db.execute(select(Case))
        cases = res_cases.scalars().all()

        if not cases:
            logger.info("Seeding demonstration cases and evidence chains...")
            case1 = Case(
                case_number="SHIELD-MH-2026-000001",
                fir_number="FIR-402/2026",
                title="Operation Red Dawn: Cross-Border Cyber Exfiltration",
                description="Intelligence alert regarding unauthorized intrusion attempts into critical port infrastructure and encrypted communications.",
                category=CrimeCategory.CYBERCRIME,
                priority=CasePriority.CRITICAL,
                status=CaseStatus.UNDER_INVESTIGATION,
                incident_date=datetime.now(timezone.utc).isoformat(),
                incident_location="Gateway Terminal, Mumbai Port",
                assigned_officer_id=sp.id,
                created_by_officer_id=dgp.id,
                department="STATE_POLICE",
                ai_summary="ARIA Preliminary Analysis: Coordinated APT intrusion signatures detected across telemetry. Multi-hop proxy egress.",
                ai_tags=["cyber", "infrastructure", "high_priority"],
            )
            db.add(case1)
            await db.flush()

            suspect1 = Suspect(
                case_id=case1.id,
                full_name="Tariq Mansoor",
                aliases=["The Phantom", "Cipher7"],
                nationality="Unknown",
                notes="Key person of interest handling relay communications.",
            )
            db.add(suspect1)

            evidence1 = Evidence(
                case_id=case1.id,
                evidence_number=f"EV-{case1.case_number}-0001",
                title="Firewall Intrusion Packet Dump",
                evidence_type=EvidenceType.DIGITAL,
                file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                collected_by_id=sp.id,
                collected_at=datetime.now(timezone.utc).isoformat(),
            )
            db.add(evidence1)

            case2 = Case(
                case_number="SHIELD-MH-2026-000002",
                fir_number="FIR-819/2026",
                title="Inter-State Hawala & Syndicate Laundering",
                description="Tracking illicit transaction channels routing funds via shell corporate entities across multiple jurisdictions.",
                category=CrimeCategory.MONEY_LAUNDERING,
                priority=CasePriority.HIGH,
                status=CaseStatus.OPEN,
                incident_date=datetime.now(timezone.utc).isoformat(),
                incident_location="Bandra Kurla Complex, Mumbai",
                assigned_officer_id=sp.id,
                created_by_officer_id=sp.id,
                department="STATE_POLICE",
                ai_summary="ARIA Preliminary Analysis: Multiple shell entity registrations linked to single notary.",
                ai_tags=["hawala", "financial", "syndicate"],
            )
            db.add(case2)

            audit = AuditLog(
                officer_id=dgp.id,
                action=AuditAction.LOGIN,
                ip_address="127.0.0.1",
                timestamp=datetime.now(timezone.utc).isoformat(),
                details={"system": "initial_seed"},
            )
            db.add(audit)

        await db.commit()
        logger.info("✅ Database auto-seed check completed successfully.")
