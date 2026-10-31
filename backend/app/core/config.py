"""
SHIELD Platform — Core Configuration
Production-ready settings with environment variable support.
"""
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator
from typing import List, Optional
import secrets


class Settings(BaseSettings):
    # ─── App ───────────────────────────────────────────────
    APP_NAME: str = "SHIELD - Law Enforcement Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # development | staging | production

    # ─── Security ──────────────────────────────────────────
    SECRET_KEY: str = secrets.token_urlsafe(64)
    JWT_ALGORITHM: str = "RS256"           # Asymmetric — more secure than HS256
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access tokens
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MFA_TOTP_ISSUER: str = "SHIELD-GOV-IN"

    # ─── Database ──────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://shield:shield@localhost:5432/shielddb"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # ─── Redis ─────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SESSION_DB: int = 1
    REDIS_RATE_LIMIT_DB: int = 2

    # ─── MinIO (Evidence Storage) ──────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_SECURE: bool = True
    MINIO_BUCKET_EVIDENCE: str = "shield-evidence"
    MINIO_BUCKET_CCTV: str = "shield-cctv"

    # ─── CORS ──────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "https://shield.gov.in",
        "https://app.shield.gov.in",
    ]

    # ─── Rate Limiting ─────────────────────────────────────
    RATE_LIMIT_LOGIN: str = "5/minute"    # Anti-brute-force
    RATE_LIMIT_API: str = "100/minute"    # General API
    RATE_LIMIT_AI: str = "20/minute"      # AI endpoints (expensive)

    # ─── Encryption ────────────────────────────────────────
    FIELD_ENCRYPTION_KEY: str = ""        # Must be set in environment (Fernet key)

    # ─── AI / ARIA ─────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"     # Use local model — no data leaves server
    AI_MAX_TOKENS: int = 4096

    # ─── Monitoring ────────────────────────────────────────
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"

    # ─── Keycloak (Enterprise Auth) ───────────────────────
    KEYCLOAK_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "shield"
    KEYCLOAK_CLIENT_ID: str = "shield-api"
    KEYCLOAK_CLIENT_SECRET: str = ""

    # ─── Duty Mode ─────────────────────────────────────────
    DUTY_GPS_INTERVAL_SECONDS: int = 30
    DUTY_DEAD_OFFICER_ALERT_MINUTES: int = 30
    DUTY_GEOFENCE_RADIUS_METERS: int = 5000

    # ─── Traitor Detection ─────────────────────────────────
    TRAITOR_MEDIUM_THRESHOLD: int = 31
    TRAITOR_HIGH_THRESHOLD: int = 61
    TRAITOR_CRITICAL_THRESHOLD: int = 81
    TRAITOR_ANALYSIS_INTERVAL_HOURS: int = 1

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
