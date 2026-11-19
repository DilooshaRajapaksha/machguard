import json
from datetime import datetime, timezone
from typing import Optional

from . import db
from .notification_schemas import NotificationCreate


CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key TEXT NOT NULL UNIQUE,
    machine_id TEXT NOT NULL,
    severity TEXT NOT NULL
        CHECK (severity IN ('info', 'watch', 'warning', 'fault')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    source TEXT NOT NULL
        CHECK (source IN ('simulated', 'measured', 'unknown')),
    reading_timestamp TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    suggestions_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    acknowledged_at TEXT,
    acknowledged_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_notifications_machine_id
    ON notifications (machine_id, id DESC);

CREATE TABLE IF NOT EXISTS notification_reads (
    notification_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    read_at TEXT NOT NULL,
    PRIMARY KEY (notification_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_notification_reads_user
    ON notification_reads (user_id, notification_id);
"""


SELECT_NOTIFICATIONS = """
SELECT
    n.*,
    CASE WHEN r.notification_id IS NULL THEN 0 ELSE 1 END AS is_read
FROM notifications n
LEFT JOIN notification_reads r
    ON r.notification_id = n.id AND r.user_id = ?
"""


VISIBLE = """
(EXISTS (SELECT 1 FROM users WHERE id=? AND role='admin')
 OR EXISTS (
    SELECT 1 FROM machines m JOIN engineer_accounts a ON a.engineer_id=m.engineer_id
    WHERE m.machine_id=n.machine_id AND a.user_id=?
 ))
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_notifications() -> None:
    with db.connect() as conn:
        conn.executescript(CREATE_TABLES)


def notification_from_row(row) -> Optional[dict]:
    if row is None:
        return None

    item = dict(row)
    item.pop("event_key", None)
    item["reasons"] = json.loads(item.pop("reasons_json"))
    item["suggestions"] = json.loads(item.pop("suggestions_json"))
    item["is_read"] = bool(item.get("is_read", False))
    return item


def save_notification(
    notification: NotificationCreate,
    event_key: str,
) -> int:
    if not isinstance(event_key, str) or not event_key.strip():
        raise ValueError("A non-empty event key is required.")

    payload = notification.model_dump(mode="json")

    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO notifications (
                event_key,
                machine_id,
                severity,
                title,
                message,
                source,
                reading_timestamp,
                reasons_json,
                suggestions_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_key) DO NOTHING
            """,
            (
                event_key,
                payload["machine_id"],
                payload["severity"],
                payload["title"],
                payload["message"],
                payload["source"],
                payload["reading_timestamp"],
                json.dumps(payload["reasons"]),
                json.dumps(payload["suggestions"]),
                utc_now(),
            ),
        )

        row = conn.execute(
            "SELECT id FROM notifications WHERE event_key = ?",
            (event_key,),
        ).fetchone()

        return int(row["id"])


def get_notification(
    notification_id: int,
    user_id: int,
) -> Optional[dict]:
    with db.connect() as conn:
        row = conn.execute(
            SELECT_NOTIFICATIONS + " WHERE n.id = ? AND " + VISIBLE,
            (user_id, notification_id, user_id, user_id),
        ).fetchone()

        return notification_from_row(row)


def list_notifications(
    user_id: int,
    machine_id: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100.")

    if offset < 0:
        raise ValueError("Offset cannot be negative.")

    conditions = [VISIBLE]
    parameters = [user_id, user_id, user_id]

    if machine_id is not None:
        conditions.append("n.machine_id = ?")
        parameters.append(machine_id)

    base_where = (
        " WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    filtered_conditions = list(conditions)

    if unread_only:
        filtered_conditions.append("r.notification_id IS NULL")

    filtered_where = (
        " WHERE " + " AND ".join(filtered_conditions)
        if filtered_conditions
        else ""
    )

    count_from = """
    FROM notifications n
    LEFT JOIN notification_reads r
        ON r.notification_id = n.id AND r.user_id = ?
    """

    with db.connect() as conn:
        conn.execute("BEGIN")

        counts = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(
                    CASE WHEN r.notification_id IS NULL THEN 1 ELSE 0 END
                ), 0) AS unread_count
            """
            + count_from
            + base_where,
            parameters,
        ).fetchone()

        rows = conn.execute(
            SELECT_NOTIFICATIONS
            + filtered_where
            + " ORDER BY n.id DESC LIMIT ? OFFSET ?",
            [*parameters, limit, offset],
        ).fetchall()

        return {
            "items": [notification_from_row(row) for row in rows],
            "total": (
                counts["unread_count"]
                if unread_only
                else counts["total"]
            ),
            "unread_count": counts["unread_count"],
        }


def mark_as_read(notification_id: int, user_id: int) -> bool:
    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")

        exists = conn.execute(
            "SELECT n.id FROM notifications n WHERE n.id = ? AND " + VISIBLE,
            (notification_id, user_id, user_id),
        ).fetchone()

        if exists is None:
            return False

        conn.execute(
            """
            INSERT INTO notification_reads (
                notification_id, user_id, read_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(notification_id, user_id) DO NOTHING
            """,
            (notification_id, user_id, utc_now()),
        )

        return True


def acknowledge_notification(
    notification_id: int,
    user_id: int,
    username: str,
) -> bool:
    if not username.strip():
        raise ValueError("A username is required.")

    timestamp = utc_now()

    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")

        exists = conn.execute(
            "SELECT id FROM notifications WHERE id = ?",
            (notification_id,),
        ).fetchone()

        if exists is None:
            return False

        conn.execute(
            """
            UPDATE notifications
            SET acknowledged_at = ?, acknowledged_by = ?
            WHERE id = ? AND acknowledged_at IS NULL
            """,
            (timestamp, username, notification_id),
        )

        conn.execute(
            """
            INSERT INTO notification_reads (
                notification_id, user_id, read_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(notification_id, user_id) DO NOTHING
            """,
            (notification_id, user_id, timestamp),
        )

        return True