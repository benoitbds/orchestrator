"""Authentication helpers for the FastAPI backend."""

from __future__ import annotations

import logging
import os

import firebase_admin
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as fb_auth, credentials

from orchestrator import crud

ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.getenv("ADMIN_EMAILS", "").split(",")
    if e.strip()
}

ALLOW_ANON_AUTH = os.getenv("ALLOW_ANON_AUTH", "0").lower() in {"1", "true", "yes"}
_AUTH_OPTIONAL = False

logger = logging.getLogger(__name__)

http_bearer = HTTPBearer(auto_error=False)


def _ensure_firebase_initialized() -> None:
    """Initialise Firebase lazily when authentication is required."""

    global _AUTH_OPTIONAL

    if firebase_admin._apps:  # already configured
        return

    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

    try:
        if cred_path and os.path.exists(cred_path):
            firebase_admin.initialize_app(credentials.Certificate(cred_path))
            _AUTH_OPTIONAL = False
        else:
            if cred_path:
                logger.warning("Firebase service account file not found: %s", cred_path)
            # Use application default credentials (works for tests/local envs)
            firebase_admin.initialize_app()
            _AUTH_OPTIONAL = ALLOW_ANON_AUTH or bool(os.getenv("PYTEST_CURRENT_TEST"))
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - unexpected configuration errors
        raise HTTPException(
            status_code=503,
            detail="Firebase authentication not configured. Please check credentials.",
        ) from exc


def _load_or_create_user(uid: str, email: str | None, is_admin: bool = False) -> None:
    user = crud.get_user_by_uid(uid)
    if not user:
        crud.create_user(uid=uid, email=email, is_admin=is_admin)


def _verify_token_and_get_user(token: str) -> dict:
    try:
        token_data = fb_auth.verify_id_token(token)
    except Exception as exc:  # pragma: no cover - verification handled by Firebase
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    uid = token_data["uid"]
    email = (token_data.get("email") or "").lower()
    _load_or_create_user(uid, email, email in ADMIN_EMAILS)

    return {
        "uid": uid,
        "email": email,
        "email_verified": token_data.get("email_verified", False),
    }


def _build_test_user() -> dict:
    uid = os.getenv("DEFAULT_TEST_UID", "test-user")
    email = os.getenv("DEFAULT_TEST_EMAIL")
    _load_or_create_user(uid, email)
    return {"uid": uid, "email": email, "email_verified": False}


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(http_bearer)):
    _ensure_firebase_initialized()

    if creds is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    return _verify_token_and_get_user(creds.credentials)


def get_current_user_optional(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(http_bearer),
):
    _ensure_firebase_initialized()

    if creds is not None:
        return _verify_token_and_get_user(creds.credentials)

    if _AUTH_OPTIONAL:
        logger.debug("Using test user for %s", request.url.path)
        return _build_test_user()

    raise HTTPException(status_code=401, detail="Authentication required")

