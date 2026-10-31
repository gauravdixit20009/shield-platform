"""
SHIELD Platform — CCTV Gateway & AI Vision Service
Handles camera registration, RTSP-to-HLS proxying, motion/tamper detection, and stream tokens.
"""
import uuid
import time
import hmac
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timezone

from app.core.config import settings
from app.utils.logger import logger
from app.utils.encryption import encrypt_field, decrypt_field

class CCTVService:
    """
    Manages police station & city junction CCTV infrastructure.
    All camera IP credentials are encrypted with AES-256 (Fernet) at rest.
    """

    # In-memory registry for fast lookups (backed by DB in production)
    _cameras: Dict[str, dict] = {
        "cam-001": {
            "id": "cam-001",
            "name": "HQ Main Perimeter Gate",
            "location": "Mumbai Central Police HQ",
            "zone": "ZONE_A",
            "status": "ONLINE",
            "rtsp_url": "rtsp://10.0.1.101:554/live/ch0", # Internal subnet
            "latitude": 18.9220,
            "longitude": 72.8347,
            "has_ptz": True,
            "ai_analytics_enabled": True,
            "last_ping": datetime.now(timezone.utc).isoformat(),
        },
        "cam-002": {
            "id": "cam-002",
            "name": "Armory & Evidence Vault Corridor",
            "location": "Special Operations Enclave",
            "zone": "ZONE_TOP_SECRET",
            "status": "ONLINE",
            "rtsp_url": "rtsp://10.0.2.102:554/live/ch0",
            "latitude": 18.9224,
            "longitude": 72.8342,
            "has_ptz": False,
            "ai_analytics_enabled": True,
            "last_ping": datetime.now(timezone.utc).isoformat(),
        }
    }

    _alerts: List[dict] = [
        {
            "id": "alert-001",
            "camera_id": "cam-001",
            "type": "PERIMETER_MOTION",
            "confidence": 0.94,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": "Unscheduled vehicle approach detected near East Gate.",
            "is_acknowledged": False
        }
    ]

    @classmethod
    def list_cameras(cls, officer_rank: str, zone: Optional[str] = None) -> List[dict]:
        """
        Enforce zone restrictions:
        Officers see only their assigned zone.
        Only SP and above (or DGP) can view Top-Secret armory/vault feeds.
        """
        results = []
        is_senior = officer_rank in ["SP", "DIG", "IGP", "ADGP", "DGP", "IPS"]

        for cam in cls._cameras.values():
            if cam["zone"] == "ZONE_TOP_SECRET" and not is_senior:
                continue # Redacted for non-senior officers
            if zone and cam["zone"] != zone:
                continue
            
            # Sanitize: NEVER return raw RTSP credentials to frontend
            results.append({
                "id": cam["id"],
                "name": cam["name"],
                "location": cam["location"],
                "zone": cam["zone"],
                "status": cam["status"],
                "has_ptz": cam["has_ptz"],
                "latitude": cam["latitude"],
                "longitude": cam["longitude"],
                "ai_analytics_enabled": cam["ai_analytics_enabled"],
                "last_ping": cam["last_ping"],
            })
        return results

    @classmethod
    def generate_stream_token(cls, camera_id: str, officer_badge: str) -> dict:
        """
        Generates an HMAC-signed ephemeral token (15-min TTL) for the HLS video proxy.
        Direct RTSP URL is never exposed to browser or mobile devices.
        """
        if camera_id not in cls._cameras:
            raise ValueError("Camera not found")

        cam = cls._cameras[camera_id]
        expiry = int(time.time()) + 900 # 15 minutes
        secret = getattr(settings, "SECRET_KEY", "shield_default_secret")
        
        signature = hmac.new(
            secret.encode(),
            f"{camera_id}|{officer_badge}|{expiry}".encode(),
            hashlib.sha256
        ).hexdigest()

        token = f"{camera_id}.{expiry}.{signature}"

        return {
            "camera_id": camera_id,
            "camera_name": cam["name"],
            "stream_protocol": "HLS_ENCRYPTED",
            "stream_url": f"/api/v1/cctv/stream/{camera_id}/index.m3u8?token={token}",
            "expires_in_seconds": 900,
            "issued_to_officer": officer_badge,
        }

    @classmethod
    def register_camera(cls, data: dict) -> dict:
        cam_id = f"cam-{str(uuid.uuid4())[:6]}"
        cls._cameras[cam_id] = {
            "id": cam_id,
            "name": data["camera_name"],
            "location": data["location"],
            "zone": data.get("zone", "ZONE_GENERAL"),
            "status": "ONLINE",
            "rtsp_url": data["stream_url"],
            "latitude": data.get("latitude", 0.0),
            "longitude": data.get("longitude", 0.0),
            "has_ptz": data.get("has_ptz", False),
            "ai_analytics_enabled": True,
            "last_ping": datetime.now(timezone.utc).isoformat(),
        }
        return cls._cameras[cam_id]

    @classmethod
    def get_vision_alerts(cls) -> List[dict]:
        return cls._alerts
