import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from django.conf import settings

import msal
import requests


# Reserved OpenID Connect scopes that must not be passed to Graph app scopes
RESERVED = {"openid", "profile", "offline_access"}

CLIENT_ID = os.environ.get("GRAPH_CLIENT_ID", "")
TENANT = os.environ.get("GRAPH_TENANT_ID", "common")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT}"

# Read scopes from env, filter out reserved
_raw_scopes = os.environ.get("GRAPH_SCOPES", "Mail.Send").split()
GRAPH_SCOPES: List[str] = [s for s in _raw_scopes if s and s not in RESERVED]


# User-specific cache management
BASE_DIR = Path(__file__).resolve().parents[2]
_user_caches: Dict[int, msal.SerializableTokenCache] = {}


def get_user_cache_file(user_id: int) -> Path:
    """Get cache file path for a specific user."""
    cache_dir = Path(settings.DATA_STORAGE_PATH) / "msal_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"user_{user_id}_cache.bin"


def load_user_cache(user_id: int) -> msal.SerializableTokenCache:
    """Load cache for a specific user."""
    if user_id not in _user_caches:
        cache = msal.SerializableTokenCache()
        cache_file = get_user_cache_file(user_id)
        try:
            if cache_file.exists():
                cache.deserialize(cache_file.read_text())
        except Exception:
            # Corrupt cache; ignore
            pass
        _user_caches[user_id] = cache
    return _user_caches[user_id]


def save_user_cache(user_id: int) -> None:
    """Save cache for a specific user."""
    if user_id in _user_caches:
        try:
            cache_file = get_user_cache_file(user_id)
            cache_file.write_text(_user_caches[user_id].serialize())
        except Exception:
            # Best-effort persistence
            pass


def clear_user_cache(user_id: int) -> None:
    """Clear cache for a specific user (e.g., on logout)."""
    global _user_caches
    try:
        # Remove from memory
        if user_id in _user_caches:
            del _user_caches[user_id]
        
        # Delete cache file
        cache_file = get_user_cache_file(user_id)
        if cache_file.exists():
            cache_file.unlink()
    except Exception as e:
        # Best-effort cleanup
        pass


def get_app(user_id: int = None) -> msal.PublicClientApplication:
    """Get MSAL app for a specific user or global fallback."""
    if user_id is not None:
        token_cache = load_user_cache(user_id)
    else:
        # Fallback to global cache for backward compatibility
        token_cache = msal.SerializableTokenCache()
        global_cache_file = BASE_DIR / "msal_cache.bin"
        try:
            if global_cache_file.exists():
                token_cache.deserialize(global_cache_file.read_text())
        except Exception:
            pass
    
    return msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
        token_cache=token_cache,
    )


class NeedsLoginError(Exception):
    pass


def acquire_token_silent(user_id: int = None) -> Optional[str]:
    if not CLIENT_ID:
        return None
    app = get_app(user_id)
    accounts = app.get_accounts()
    account = accounts[0] if accounts else None
    result: Optional[dict] = app.acquire_token_silent(GRAPH_SCOPES, account=account)
    if result and "access_token" in result:
        return str(result["access_token"])
    return None


def acquire_token_silent_or_fail(user_id: int = None) -> str:
    token = acquire_token_silent(user_id)
    if not token:
        raise NeedsLoginError("Please sign in via Device Code first")
    return token


def device_code_start(user_id: int = None) -> Optional[dict]:
    if not CLIENT_ID:
        return None
    app = get_app(user_id)
    flow = app.initiate_device_flow(scopes=GRAPH_SCOPES)
    return flow


def start_device_code_flow(user_id: int = None) -> Optional[dict]:
    """Alias for device_code_start for backwards compatibility."""
    return device_code_start(user_id)


def device_code_poll(flow: dict, timeout: int = 2, user_id: int = None) -> dict:
    try:
        app = get_app(user_id)
        result = app.acquire_token_by_device_flow(flow, timeout=timeout)
        if result and "access_token" in result:
            if user_id is not None:
                save_user_cache(user_id)
            return {"status": "ok"}
        # When still pending, msal returns None or raises Timeout; treat as pending
        return {"status": "pending"}
    except msal.exceptions.MsalServiceError as e:
        return {"status": "error", "detail": getattr(e, "error", str(e))}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def poll_device_code(device_code: str, timeout: int = 2) -> Optional[dict]:
    """Alias for device_code_poll for backwards compatibility."""
    # Note: This expects a device code string, but the actual flow needs the full flow dict
    # This is kept for compatibility but may need the full flow dict stored in session
    return device_code_poll({"device_code": device_code}, timeout=timeout)


def send_mail(access_token: str, message_payload: dict, timeout: int = 15) -> bool:
    """Send a mail using Graph. Raises for HTTP errors."""
    url = "https://graph.microsoft.com/v1.0/me/sendMail"
    headers = {"Authorization": f"Bearer {access_token}"}
    body = {"message": message_payload, "saveToSentItems": True}
    resp = requests.post(url, json=body, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return True


def send_mail_with_attachments(access_token: str, message_payload: dict, attachments: List[dict] = None, timeout: int = 15) -> bool:
    """Send a mail with attachments using Graph. Raises for HTTP errors."""
    url = "https://graph.microsoft.com/v1.0/me/sendMail"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Add attachments to message payload if provided
    if attachments:
        message_payload["attachments"] = attachments
    
    body = {"message": message_payload, "saveToSentItems": True}
    resp = requests.post(url, json=body, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return True


