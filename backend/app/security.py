from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as fb_auth

http_bearer = HTTPBearer(auto_error=False)

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(http_bearer)):
    if creds is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        t = fb_auth.verify_id_token(creds.credentials)
        return {
            "uid": t["uid"],
            "email": t.get("email"),
            "email_verified": t.get("email_verified", False),
        }
    except Exception as e:  # pragma: no cover - verification details handled by Firebase
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
