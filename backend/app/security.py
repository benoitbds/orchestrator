import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as fb_auth
from orchestrator import crud

ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.getenv("ADMIN_EMAILS", "").split(",")
    if e.strip()
}

http_bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(http_bearer)):
    if creds is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        t = fb_auth.verify_id_token(creds.credentials)
    except Exception as e:  # pragma: no cover - verification details handled by Firebase
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    uid = t["uid"]
    email = (t.get("email") or "").lower()
    u = crud.get_user_by_uid(uid)
    if not u:
        crud.create_user(uid=uid, email=email, is_admin=(email in ADMIN_EMAILS))
    return {
        "uid": uid,
        "email": email,
        "email_verified": t.get("email_verified", False),
    }
