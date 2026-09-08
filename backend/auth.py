"""
Authentication & authorization.

Two roles: "agent" (submits their own data to get scored) and "admin"
(oversees agents, sees the monitoring dashboard and all logged
predictions). Agents self-register via /auth/register and are active
immediately. Admin accounts are NOT self-registrable — they're seeded
at startup from ADMIN_USERNAME/ADMIN_PASSWORD env vars (see app.py),
so someone can't just sign up and grant themselves admin.

JWT bearer tokens, stateless. Set JWT_SECRET_KEY in your environment —
generate one with:
    python -c "import secrets; print(secrets.token_hex(32))"
"""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY environment variable is not set. Generate one with: "
        "python -c \"import secrets; print(secrets.token_hex(32))\" and set it "
        "in your .env file."
    )

# tokenUrl points Swagger's "Authorize" button at /auth/login.
# auto_error=False so we can return our own 401 with a clear message.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: int, username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "user_id": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired, please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token.")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Decodes the bearer token into {user_id, username, role}. Does NOT
    check the account is still active — call get_current_active_user for
    routes where a disabled agent should be locked out immediately."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    try:
        from db import is_session_revoked
    except ImportError:
        from .db import is_session_revoked
    if is_session_revoked(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked, please log in again.")
    return {"user_id": payload["user_id"], "username": payload["sub"], "role": payload["role"]}


def require_role(*allowed_roles: str):
    """Dependency factory: Depends(require_role("admin")) or
    Depends(require_role("agent", "admin"))."""

    def _check(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires role: {' or '.join(allowed_roles)}.",
            )
        return current_user

    return _check