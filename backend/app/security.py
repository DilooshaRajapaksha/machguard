import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import users

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
TOKEN_HOURS = 8
MIN_PASSWORD_LENGTH = 10
LOCK_AFTER_FAILURES = 5
LOCK_MINUTES = 15

bearer = HTTPBearer(auto_error=False)
_secret_cache = None


def get_secret() -> str:
    global _secret_cache
    if _secret_cache:
        return _secret_cache
    key = os.environ.get("MACHGUARD_SECRET")
    if not key and ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("MACHGUARD_SECRET="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        key = secrets.token_hex(32)
        existing = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
        prefix = "" if existing == "" or existing.endswith("\n") else "\n"
        with open(ENV_FILE, "a", encoding="utf-8") as handle:
            handle.write(prefix + "MACHGUARD_SECRET=" + key + "\n")
    _secret_cache = key
    return key


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$16384$8$1$" + salt.hex() + "$" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=bytes.fromhex(salt_hex),
            n=int(n), r=int(r), p=int(p), dklen=len(digest_hex) // 2,
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


DUMMY_HASH = hash_password("not-a-real-password-0")


def check_password_rules(password: str, username: str = "") -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"The password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("The password must contain at least one letter and one number.")
    if username and username.lower() in password.lower():
        raise ValueError("The password must not contain the username.")


def create_token(user: dict) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    payload = {"sub": str(user["id"]), "ver": user["token_version"], "exp": expires}
    return jwt.encode(payload, get_secret(), algorithm="HS256")


def _load_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    problem = HTTPException(
        status_code=401,
        detail="Please log in.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise problem
    try:
        payload = jwt.decode(credentials.credentials, get_secret(), algorithms=["HS256"])
        user = users.get(int(payload["sub"]))
    except Exception:
        raise problem
    if not user or not user["is_active"] or user["token_version"] != payload.get("ver"):
        raise problem
    return user


def current_user_any(user: dict = Depends(_load_user)) -> dict:
    return user


def current_user(user: dict = Depends(_load_user)) -> dict:
    if user["must_change_password"]:
        raise HTTPException(status_code=403, detail="password_change_required")
    return user


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can do this.")
    return user