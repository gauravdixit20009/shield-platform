"""
SHIELD Platform — Database Seed Script
Creates initial officers, cases, and credentials for development and testing.
"""
import asyncio
import pyotp
from datetime import datetime, timezone

from app.core.database import AsyncSessionLocal, engine, Base
from app.models.officer import Officer, OfficerRank, Department
from app.models.case import Case, CasePriority, CaseStatus, CrimeCategory, Suspect, Evidence, EvidenceType
from app.auth.auth_service import AuthService
from app.models.audit import AuditLog, AuditAction

DEV_TOTP_SECRET = "JBSWY3DPEHPK3PXP"  # Standard base32 test secret

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        from sqlalchemy import select
        res = await db.execute(select(Officer).where(Officer.badge_number == "DGP-INDIA-01"))
        if res.scalar_one_or_none():
            print("Database already seeded.")
            return

        print("Seeding initial officers and cases...")

        hashed_pw = AuthService.hash_password("Password@123")

        # 1. DGP Officer
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
            threat_level="LOW",
            threat_score=5,
        )
        db.add(dgp)
        await db.flush()

        # 2. IPS Officer (SP rank)
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
            is_on_duty=True,
            threat_level="LOW",
            threat_score=10,
            superior_officer_id=dgp.id,
        )
        db.add(sp)
        await db.flush()

        # 3. Seed Cases
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
            ai_summary="ARIA Preliminary Analysis: Coordinated APT intrusion signatures detected across telemetry. IP endpoints match known proxy infrastructure.",
            ai_tags=["cyber", "infrastructure", "high_priority"],
        )
        db.add(case1)
        await db.flush()

        # Suspect
        suspect1 = Suspect(
            case_id=case1.id,
            full_name="Tariq Mansoor",
            aliases=["The Phantom", "Cipher7"],
            nationality="Unknown",
            notes="Key person of interest handling relay communications.",
        )
        db.add(suspect1)

        # Evidence
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

        # Case 2
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

        # Initial Audit Log
        audit = AuditLog(
            officer_id=dgp.id,
            action=AuditAction.LOGIN,
            ip_address="127.0.0.1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            details={"system": "initial_seed"},
        )
        db.add(audit)

        await db.commit()
        print("Database seeded successfully with demo officers and cases!")

if __name__ == "__main__":
    asyncio.run(seed())
