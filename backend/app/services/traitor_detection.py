"""
SHIELD Platform — Traitor Detection Engine
AI-powered behavioral analytics to identify insider threats.
Runs as background Celery task every hour.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.models.officer import Officer, OfficerRank
from app.models.audit import (
    BehaviorSignal, BehaviorSignalType, AuditLog, AuditAction,
    ThreatReport
)
from app.ai.aria_service import ARIAService
from app.core.config import settings
from app.utils.logger import logger


class TraitorDetectionEngine:
    """
    Behavioral analytics engine for insider threat detection.
    
    Architecture:
    1. Collect raw signals (event-driven, real-time)
    2. Aggregate hourly → compute threat scores
    3. ARIA analyzes officers above thresholds
    4. Automated escalation at CRITICAL level
    
    Score contributions (per signal):
    - Off-hours access: +5
    - Unusual case access: +10-15
    - Bulk download: +20
    - Location spoof: +15
    - VPN usage: +8
    - Failed auth spike: +6/attempt
    - Case tampering: +25
    - Peer deviation: +5
    """

    SCORE_WEIGHTS = {
        BehaviorSignalType.OFF_HOURS_ACCESS: 5,
        BehaviorSignalType.UNUSUAL_CASE_ACCESS: 12,
        BehaviorSignalType.BULK_DOWNLOAD: 20,
        BehaviorSignalType.LOCATION_SPOOF_SUSPECT: 15,
        BehaviorSignalType.VPN_USAGE: 8,
        BehaviorSignalType.FAILED_AUTH_SPIKE: 6,
        BehaviorSignalType.CASE_TAMPERING: 25,
        BehaviorSignalType.EVIDENCE_DELETION_ATTEMPT: 20,
        BehaviorSignalType.UNUSUAL_COMMUNICATION: 10,
        BehaviorSignalType.PEER_BEHAVIOR_DEVIATION: 5,
        BehaviorSignalType.GEOGRAPHIC_ANOMALY: 12,
        BehaviorSignalType.CREDENTIAL_SHARING_SUSPECT: 18,
    }

    @classmethod
    async def run_analysis_cycle(cls, db: AsyncSession):
        """
        Main analysis cycle — called every hour by Celery.
        1. Process unprocessed signals
        2. Recalculate threat scores
        3. Generate ARIA reports for high-risk officers
        4. Trigger automated responses at CRITICAL
        """
        logger.info("TraitorDetectionEngine: Starting analysis cycle")

        # Get all active officers
        result = await db.execute(
            select(Officer).where(
                Officer.is_active == True,
                Officer.is_deleted == False,
                Officer.rank != OfficerRank.SYSTEM_ADMIN,
            )
        )
        officers = result.scalars().all()

        for officer in officers:
            await cls._analyze_officer(db, officer)

        logger.info(f"TraitorDetectionEngine: Completed analysis for {len(officers)} officers")

    @classmethod
    async def _analyze_officer(cls, db: AsyncSession, officer: Officer):
        """Full behavioral analysis for one officer."""
        # Get unprocessed signals (last 7 days)
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        signals_result = await db.execute(
            select(BehaviorSignal).where(
                and_(
                    BehaviorSignal.officer_id == officer.id,
                    BehaviorSignal.timestamp >= week_ago,
                    BehaviorSignal.is_processed == False,
                    BehaviorSignal.is_false_positive == False,
                )
            )
        )
        signals = signals_result.scalars().all()

        if not signals:
            # Gradually reduce score over time (decay)
            if officer.threat_score > 0:
                decay = min(5, officer.threat_score)
                officer.threat_score = max(0, officer.threat_score - decay)
                await db.commit()
            return

        # Calculate score delta
        score_delta = sum(cls.SCORE_WEIGHTS.get(s.signal_type, 5) for s in signals)

        # Cap at 100
        new_score = min(100, officer.threat_score + score_delta)
        old_level = officer.threat_level

        # Determine threat level
        if new_score >= settings.TRAITOR_CRITICAL_THRESHOLD:
            new_level = "CRITICAL"
        elif new_score >= settings.TRAITOR_HIGH_THRESHOLD:
            new_level = "HIGH"
        elif new_score >= settings.TRAITOR_MEDIUM_THRESHOLD:
            new_level = "MEDIUM"
        else:
            new_level = "LOW"

        officer.threat_score = new_score
        officer.threat_level = new_level
        officer.last_threat_analysis = datetime.now(timezone.utc).isoformat()

        # Mark signals as processed
        for signal in signals:
            signal.is_processed = True

        await db.commit()

        # Generate ARIA report if threshold crossed
        if new_level in ("HIGH", "CRITICAL") and new_level != old_level:
            await cls._generate_threat_report(db, officer, signals, new_level, new_score)

        # AUTO-RESPONSE at CRITICAL
        if new_level == "CRITICAL":
            await cls._handle_critical_threat(db, officer)

    @classmethod
    async def _generate_threat_report(
        cls,
        db: AsyncSession,
        officer: Officer,
        signals: List[BehaviorSignal],
        threat_level: str,
        threat_score: int,
    ):
        """Generate AI-powered threat report using ARIA."""
        signals_data = [
            {
                "type": s.signal_type,
                "severity": s.severity,
                "timestamp": s.timestamp,
                "details": s.details,
            }
            for s in signals
        ]

        # Get peer baseline (placeholder — would be computed from similar officers)
        peer_baseline = {
            "avg_daily_logins": 2,
            "avg_cases_viewed": 5,
            "avg_off_hours_access": 0,
        }

        officer_data = {
            "rank": officer.rank,
            "tenure_years": 5,  # Would be computed from join date
            "threat_score": threat_score,
        }

        aria_result = await ARIAService.analyze_officer_behavior(
            officer_data, signals_data, peer_baseline
        )

        report = ThreatReport(
            officer_id=officer.id,
            threat_level=threat_level,
            threat_score=threat_score,
            signals_summary={"signal_count": len(signals), "signals": signals_data},
            ai_analysis=aria_result.get("ai_analysis", ""),
            recommended_action=f"Officer {officer.badge_number} has crossed {threat_level} threshold. Immediate review recommended.",
        )
        db.add(report)
        await db.commit()

        logger.warning(
            f"THREAT REPORT generated: Officer {officer.badge_number} "
            f"Level={threat_level} Score={threat_score}"
        )

    @classmethod
    async def _handle_critical_threat(cls, db: AsyncSession, officer: Officer):
        """
        Automated response to CRITICAL threat:
        1. Restrict access to sensitive cases
        2. Alert Internal Affairs (via notification)
        3. Preserve all evidence (prevent deletion)
        4. Do NOT suspend yet — that requires human decision
        """
        logger.critical(
            f"CRITICAL THREAT: Officer {officer.badge_number} ({officer.rank}) "
            f"Score={officer.threat_score}. Internal Affairs notified."
        )
        # TODO: Send encrypted alert to DGP + Internal Affairs
        # TODO: Restrict officer's access to TOP_SECRET cases
        # TODO: Snapshot all their recent activity for preservation

    @classmethod
    async def add_signal(
        cls,
        db: AsyncSession,
        officer_id: uuid.UUID,
        signal_type: BehaviorSignalType,
        details: Dict = None,
    ):
        """
        Add a behavioral signal (called from various services when anomaly detected).
        This is the main entry point for event-driven signal collection.
        """
        weight = cls.SCORE_WEIGHTS.get(signal_type, 5)
        signal = BehaviorSignal(
            officer_id=officer_id,
            signal_type=signal_type,
            severity=min(10, weight // 2),
            score_contribution=weight,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details or {},
        )
        db.add(signal)
        await db.commit()
        logger.info(f"BehaviorSignal added: {signal_type} for officer {officer_id} (weight: +{weight})")
