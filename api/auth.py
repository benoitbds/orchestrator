import os
from fastapi import HTTPException, Request, status
import firebase_admin
from firebase_admin import auth, credentials
from typing import Optional
import logging

logger = logging.getLogger(__name__)

cred_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
if cred_path and not firebase_admin._apps:
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        logger.info(f"Firebase initialized with service account: {cred_path}")
    else:
        logger.warning(f"Firebase service account file not found: {cred_path}. Using default credentials.")
        firebase_admin.initialize_app()

async def verify_id_token(token: str) -> dict:
    try:
        return auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid auth token')

async def get_current_user(request: Request) -> Optional[dict]:
    header = request.headers.get('Authorization')
    if not header or not header.startswith('Bearer '):
        return None
    token = header.split(' ', 1)[1]
    return await verify_id_token(token)
