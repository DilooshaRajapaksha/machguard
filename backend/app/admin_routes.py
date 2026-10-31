import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from . import security, users
from .admin_schemas import ResetPasswordIn, UserCreate, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users", status_code=201)
def create_user(body: UserCreate, admin: dict = Depends(security.require_admin)):
    try:
        security.check_password_rules(body.password, body.username)
    except ValueError as problem:
        raise HTTPException(status_code=400, detail=str(problem))
    try:
        new_id = users.create(
            body.username, body.full_name.strip(), security.hash_password(body.password),
            body.role, must_change=True,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="That username is already taken.")
    users.audit(admin["username"], "user_created", body.username, "role " + body.role)
    return users.public(users.get(new_id))


@router.get("/users")
def list_users(admin: dict = Depends(security.require_admin)):
    return [users.public(user) for user in users.list_all()]


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserUpdate, admin: dict = Depends(security.require_admin)):
    target = users.get(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="No such user.")
    if target["id"] == admin["id"] and (body.role is not None or body.is_active is not None):
        raise HTTPException(status_code=400, detail="You cannot change your own role or switch yourself off.")
    users.update(user_id, body.full_name, body.role, body.is_active)
    users.audit(admin["username"], "user_updated", target["username"], body.model_dump_json(exclude_none=True))
    return users.public(users.get(user_id))


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, body: ResetPasswordIn, admin: dict = Depends(security.require_admin)):
    target = users.get(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="No such user.")
    try:
        security.check_password_rules(body.new_password, target["username"])
    except ValueError as problem:
        raise HTTPException(status_code=400, detail=str(problem))
    users.set_password(user_id, security.hash_password(body.new_password), must_change=True)
    users.audit(admin["username"], "password_reset", target["username"])
    return {"reset": True, "note": "The person must choose a new password at their next login."}


@router.get("/audit")
def audit_trail(limit: int = Query(100, ge=1, le=1000), admin: dict = Depends(security.require_admin)):
    return users.list_audit(limit)