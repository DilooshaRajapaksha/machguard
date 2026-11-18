from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from . import security, users
from .admin_schemas import ChangePasswordIn, LoginIn

router = APIRouter(prefix="/auth", tags=["login"])


@router.post("/login")
def login(body: LoginIn):
    wrong = HTTPException(status_code=401, detail="Wrong username or password.")
    user = users.get_by_username(body.username.strip())
    if user is None:
        security.verify_password(body.password, security.DUMMY_HASH)
        raise wrong
    if user["locked_until"]:
        until = datetime.fromisoformat(user["locked_until"])
        if until > datetime.now(timezone.utc):
            minutes = int((until - datetime.now(timezone.utc)).total_seconds() // 60) + 1
            raise HTTPException(status_code=429, detail=f"Too many wrong tries. Try again in {minutes} minutes.")
    good = security.verify_password(body.password, user["password_hash"])
    if not good or not user["is_active"]:
        lock_until = (datetime.now(timezone.utc) + timedelta(minutes=security.LOCK_MINUTES)).isoformat()
        locked = users.record_failure(user["id"], security.LOCK_AFTER_FAILURES, lock_until)
        users.audit(user["username"], "login_failed", detail="account locked" if locked else "")
        raise wrong
    users.record_success(user["id"])
    users.audit(user["username"], "login")
    fresh = users.get(user["id"])
    return {
        "access_token": security.create_token(fresh),
        "token_type": "bearer",
        "role": fresh["role"],
        "must_change_password": bool(fresh["must_change_password"]),
    }


@router.get("/me")
def me(user: dict = Depends(security.current_user_any)):
    return users.public(user)


@router.post("/change-password")
def change_password(body: ChangePasswordIn, user: dict = Depends(security.current_user_any)):
    if not security.verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Your current password is not correct.")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=400, detail="Choose a different password from the old one.")
    try:
        security.check_password_rules(body.new_password, user["username"])
    except ValueError as problem:
        raise HTTPException(status_code=400, detail=str(problem))
    users.set_password(user["id"], security.hash_password(body.new_password), must_change=False)
    users.audit(user["username"], "password_changed")
    fresh = users.get(user["id"])
    return {"access_token": security.create_token(fresh), "token_type": "bearer"}