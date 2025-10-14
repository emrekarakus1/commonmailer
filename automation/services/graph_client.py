import os
from pathlib import Path
from typing import List, Optional

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


# Persistent cache on disk under project base
BASE_DIR = Path(__file__).resolve().parents[2]
_CACHE_FILE = BASE_DIR / "msal_cache.bin"
_token_cache = msal.SerializableTokenCache()


def load_cache() -> None:
    try:
        if _CACHE_FILE.exists():
            _token_cache.deserialize(_CACHE_FILE.read_text())
    except Exception:
        # Corrupt cache; ignore
        pass


def save_cache() -> None:
    try:
        _CACHE_FILE.write_text(_token_cache.serialize())
    except Exception:
        # Best-effort persistence
        pass


def get_app() -> msal.PublicClientApplication:
    load_cache()
    return msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
        token_cache=_token_cache,
    )


class NeedsLoginError(Exception):
    pass


def acquire_token_silent() -> Optional[str]:
    if not CLIENT_ID:
        return None
    app = get_app()
    accounts = app.get_accounts()
    account = accounts[0] if accounts else None
    result: Optional[dict] = app.acquire_token_silent(GRAPH_SCOPES, account=account)
    if result and "access_token" in result:
        return str(result["access_token"])
    return None


def acquire_token_silent_or_fail() -> str:
    token = acquire_token_silent()
    if not token:
        raise NeedsLoginError("Please sign in via Device Code first")
    return token


def device_code_start() -> Optional[dict]:
    if not CLIENT_ID:
        return None
    app = get_app()
    flow = app.initiate_device_flow(scopes=GRAPH_SCOPES)
    return flow


def start_device_code_flow() -> Optional[dict]:
    """Alias for device_code_start for backwards compatibility."""
    return device_code_start()


def device_code_poll(flow: dict, timeout: int = 2) -> dict:
    try:
        app = get_app()
        result = app.acquire_token_by_device_flow(flow, timeout=timeout)
        if result and "access_token" in result:
            save_cache()
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


