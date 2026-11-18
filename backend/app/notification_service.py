import hashlib
import json
from datetime import timezone
from typing import Optional

from . import db, notification_db
from .notification_schemas import MachineWarningOut, NotificationCreate


ALERT_STATUSES = {"watch", "warning", "fault"}

TITLES = {
    "watch": "Unusual readings detected",
    "warning": "Early warning detected",
    "fault": "Fault or limit breach detected",
    "normal": "Readings returned to normal",
}

CREATE_STATE_TABLE = """
CREATE TABLE IF NOT EXISTS notification_state (
    machine_id TEXT NOT NULL,
    source TEXT NOT NULL,
    stream_id TEXT NOT NULL,
    signature TEXT NOT NULL,
    status TEXT NOT NULL,
    reading_time REAL NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (machine_id, source, stream_id)
);
"""


def init_notification_service() -> None:
    notification_db.init_notifications()

    with db.connect() as conn:
        conn.executescript(CREATE_STATE_TABLE)


def warning_signature(warning: MachineWarningOut) -> str:
    card_codes = sorted({
        suggestion.fault_code
        for suggestion in warning.suggestions
        if suggestion.fault_code
    })

    reported_faults = sorted({
        reason
        for reason in warning.reasons
        if reason.startswith("Reported fault code:")
    })

    identity = {
        "status": warning.status,
        "card_codes": card_codes,
        "reported_faults": reported_faults,
    }

    return hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode("utf-8")
    ).hexdigest()


def record_warning(
    warning: MachineWarningOut,
    stream_id: str = "default",
) -> Optional[int]:
    if not stream_id.strip():
        raise ValueError("A stream ID is required.")

    if warning.status not in ALERT_STATUSES | {"normal"}:
        return None

    if warning.latest_reading_at is None:
        return None

    timestamp = warning.latest_reading_at

    if timestamp.utcoffset() is None:
        if warning.source != "simulated":
            raise ValueError("Non-simulated readings require a time zone.")

        timestamp = timestamp.replace(tzinfo=timezone.utc)

    reading_time = timestamp.timestamp()
    signature = warning_signature(warning)
    notification_id = None
    created_at = notification_db.utc_now()

    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")

        previous = conn.execute(
            """
            SELECT signature, status, reading_time
            FROM notification_state
            WHERE machine_id = ? AND source = ? AND stream_id = ?
            """,
            (warning.machine_id, warning.source, stream_id),
        ).fetchone()

        if previous and reading_time <= previous["reading_time"]:
            return None

        changed = previous is None or previous["signature"] != signature

        recovery = (
            warning.status == "normal"
            and previous is not None
            and previous["status"] in ALERT_STATUSES
        )

        should_notify = changed and (
            warning.status in ALERT_STATUSES or recovery
        )

        if should_notify:
            message = (
                "The latest analysis no longer detects the previous warning. "
                "This does not confirm that maintenance has been completed."
                if recovery
                else warning.message
            )

            notification = NotificationCreate(
                machine_id=warning.machine_id,
                severity="info" if recovery else warning.status,
                title=TITLES[warning.status],
                message=message,
                source=warning.source,
                reading_timestamp=warning.latest_reading_at,
                reasons=warning.reasons,
                suggestions=warning.suggestions,
            )

            payload = notification.model_dump(mode="json")

            event_identity = [
                warning.machine_id,
                warning.source,
                stream_id,
                reading_time,
                signature,
            ]

            event_key = hashlib.sha256(
                json.dumps(event_identity).encode("utf-8")
            ).hexdigest()

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
                    created_at,
                ),
            )

            saved = conn.execute(
                "SELECT id FROM notifications WHERE event_key = ?",
                (event_key,),
            ).fetchone()

            notification_id = int(saved["id"])

        conn.execute(
            """
            INSERT INTO notification_state (
                machine_id,
                source,
                stream_id,
                signature,
                status,
                reading_time,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(machine_id, source, stream_id)
            DO UPDATE SET
                signature = excluded.signature,
                status = excluded.status,
                reading_time = excluded.reading_time,
                updated_at = excluded.updated_at
            """,
            (
                warning.machine_id,
                warning.source,
                stream_id,
                signature,
                warning.status,
                reading_time,
                created_at,
            ),
        )

    return notification_id