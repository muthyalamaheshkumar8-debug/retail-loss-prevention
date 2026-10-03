from datetime import datetime, timedelta, timezone
import time
from collections import defaultdict, deque
from threading import Lock
import jwt
from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from .config import settings
from .database import db

password_hash = PasswordHash.recommended()
attempts = defaultdict(deque)
attempt_lock = Lock()
DUMMY_HASH = password_hash.hash("constant-time-invalid-account-placeholder")


def throttle(ip):
    with attempt_lock:
        now = time.monotonic()
        for key in list(attempts):
            if not attempts[key] or attempts[key][-1] < now - 300:
                del attempts[key]
        q = attempts[ip]
        while q and q[0] < now - 300:
            q.popleft()
        if len(q) >= 10:
            raise HTTPException(
                429, "Too many login attempts; try again in five minutes"
            )
        q.append(now)


def token(user_id):
    return jwt.encode(
        {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(hours=8)},
        settings.jwt_secret,
        algorithm="HS256",
    )


def current_user(request: Request):
    raw = request.cookies.get("session")
    if not raw:
        raise HTTPException(401, "Sign in required")
    try:
        claims = jwt.decode(
            raw,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired")
    user = db.users.find_one({"_id": claims["sub"], "disabled": False})
    if not user:
        raise HTTPException(401, "Account unavailable")
    return user


def admin(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Administrator access required")
    return user
