"""
Encrypted secret storage helpers for per-website integrations.

Uses Fernet symmetric encryption. Configure STORAGE_SECRETS_KEY as a
Fernet-compatible base64 key (generate with: Fernet.generate_key()).
"""

from __future__ import annotations

import json
import os
from typing import Optional, Dict, Any

from cryptography.fernet import Fernet, InvalidToken


def _get_fernet() -> Optional[Fernet]:
    key = (os.getenv("STORAGE_SECRETS_KEY") or "").strip()
    if not key:
        return None
    try:
        return Fernet(key.encode("utf-8"))
    except Exception:
        return None


def can_encrypt() -> bool:
    return _get_fernet() is not None


def encrypt_json(payload: Dict[str, Any]) -> str:
    f = _get_fernet()
    if not f:
        raise ValueError("STORAGE_SECRETS_KEY is missing or invalid")
    data = json.dumps(payload or {}, separators=(",", ":")).encode("utf-8")
    return f.encrypt(data).decode("utf-8")


def decrypt_json(token: Optional[str]) -> Dict[str, Any]:
    if not token:
        return {}
    f = _get_fernet()
    if not f:
        return {}
    try:
        raw = f.decrypt(token.encode("utf-8"))
        obj = json.loads(raw.decode("utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError):
        return {}
