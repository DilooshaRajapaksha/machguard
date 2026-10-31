from datetime import datetime, timezone
from typing import Optional

from . import db


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def public(user: Optional[dict]) -> Optional[dict]:
    if user is None:
        return None
    hidden = {"password_hash", "token_version", "failed_attempts", "locked_until"}
    shown = {key: value for key, value in user.items() if key not in hidden}
    shown["is_active"] = bool(shown["is_active"])
    shown["must_change_password"] = bool(shown["must_change_password"])
    return shown


def create(username: str, full_name: str, password_hash: str, role: str, must_change: bool) -> int:
    with db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, full_name, password_hash, role, must_change_password, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (username, full_name, password_hash, role, 1 if must_change else 0, now()),
        )
        return cur.lastrowid


def get(user_id: int) -> Optional[dict]:
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_by_username(username: str) -> Optional[dict]:
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def list_all() -> list:
    with db.connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM users ORDER BY id")]


def count_admins() -> int:
    with db.connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
        ).fetchone()[0]


def update(user_id: int, full_name=None, role=None, is_active=None) -> None:
    with db.connect() as conn:
        if full_name is not None:
            conn.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, user_id))
        if role is not None:
            conn.execute(
                "UPDATE users SET role = ?, token_version = token_version + 1 WHERE id = ?",
                (role, user_id),
            )
        if is_active is not None:
            conn.execute(
                "UPDATE users SET is_active = ?, token_version = token_version + 1 WHERE id = ?",
                (1 if is_active else 0, user_id),
            )


def set_password(user_id: int, password_hash: str, must_change: bool) -> None:
    with db.connect() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = ?, "
            "token_version = token_version + 1, failed_attempts = 0, locked_until = NULL "
            "WHERE id = ?",
            (password_hash, 1 if must_change else 0, user_id),
        )


def record_failure(user_id: int, lock_after: int, lock_until: str) -> bool:
    with db.connect() as conn:
        conn.execute("UPDATE users SET failed_attempts = failed_attempts + 1 WHERE id = ?", (user_id,))
        attempts = conn.execute("SELECT failed_attempts FROM users WHERE id = ?", (user_id,)).fetchone()[0]
        if attempts >= lock_after:
            conn.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = ? WHERE id = ?",
                (lock_until, user_id),
            )
            return True
        return False


def record_success(user_id: int) -> None:
    with db.connect() as conn:
        conn.execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login = ? WHERE id = ?",
            (now(), user_id),
        )


def audit(actor: str, action: str, target: str = "", detail: str = "") -> None:
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO audit_log (timestamp, actor, action, target, detail) VALUES (?,?,?,?,?)",
            (now(), actor, action, target, detail),
        )


def list_audit(limit: int = 100) -> list:
    with db.connect() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        )]