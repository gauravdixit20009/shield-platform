"""
SHIELD Platform — Field-Level Encryption Utility
Provides AES-GCM / Fernet encryption for sensitive PII and case fields.
"""
import base64
import os
from cryptography.fernet import Fernet
from app.core.config import settings

# Generate a default key if not provided for dev
def _get_fernet() -> Fernet:
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", None)
    if not key:
        # 32 url-safe base64-encoded bytes
        # Hardcoded fallback key for local development
        key = base64.urlsafe_b64encode(b"shield_dev_secret_key_32_bytes!!").decode("utf-8")
    elif isinstance(key, str) and len(key) != 44:
        key = base64.urlsafe_b64encode(key.encode("utf-8").ljust(32, b"#")[:32]).decode("utf-8")
    return Fernet(key.encode("utf-8") if isinstance(key, str) else key)

fernet = _get_fernet()

def encrypt_field(plain_text: str) -> str:
    """Encrypt a string field and return base64 encoded token."""
    if plain_text is None:
        return None
    return fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")

def decrypt_field(cipher_text: str) -> str:
    """Decrypt a base64 encoded token back to string."""
    if cipher_text is None:
        return None
    try:
        return fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception:
        return cipher_text
