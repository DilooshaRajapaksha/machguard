import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional
from .schemas import Reading

# The diary file. Tests can point somewhere else with MACHGUARD_DB.
DB_FILE = Path(os.environ.get(
    "MACHGUARD_DB",
    Path(__file__).resolve().parent.parent / "data" / "machguard.db",
))

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS readings (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id              TEXT NOT NULL,
    timestamp               TEXT NOT NULL,
    discharge_pressure_bar  REAL NOT NULL,
    discharge_temp_c        REAL NOT NULL,
    oil_temp_c              REAL NOT NULL,
    motor_current_a         REAL NOT NULL,
    vibration_rms           REAL,
    humidity_pct            REAL,
    fault_code              TEXT
);
CREATE INDEX IF NOT EXISTS idx_readings_machine_time
    ON readings (machine_id, timestamp);

CREATE TABLE IF NOT EXISTS fault_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id  TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    fault_code  TEXT NOT NULL
);
"""


@contextmanager
def connect():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Make the notebook pages if they do not exist yet."""
    with connect() as conn:
        conn.executescript(CREATE_TABLES)


def save_reading(r: Reading) -> int:
    """Write one reading. If it carries a NEW fault code, log a fault event too."""
    with connect() as conn:
        last = conn.execute(
            "SELECT fault_code FROM readings WHERE machine_id = ? "
            "ORDER BY timestamp DESC, id DESC LIMIT 1",
            (r.machine_id,),
        ).fetchone()
        cur = conn.execute(
            "INSERT INTO readings (machine_id, timestamp, discharge_pressure_bar, "
            "discharge_temp_c, oil_temp_c, motor_current_a, vibration_rms, "
            "humidity_pct, fault_code) VALUES (?,?,?,?,?,?,?,?,?)",
            (r.machine_id, r.timestamp.isoformat(), r.discharge_pressure_bar,
             r.discharge_temp_c, r.oil_temp_c, r.motor_current_a,
             r.vibration_rms, r.humidity_pct, r.fault_code),
        )
        previous = last["fault_code"] if last else None
        if r.fault_code and r.fault_code != previous:
            conn.execute(
                "INSERT INTO fault_events (machine_id, timestamp, fault_code) "
                "VALUES (?,?,?)",
                (r.machine_id, r.timestamp.isoformat(), r.fault_code),
            )
        return cur.lastrowid


def latest_readings(machine_id: Optional[str] = None, limit: int = 100) -> List[dict]:
    """Newest first."""
    sql = "SELECT * FROM readings"
    args: list = []
    if machine_id:
        sql += " WHERE machine_id = ?"
        args.append(machine_id)
    sql += " ORDER BY timestamp DESC, id DESC LIMIT ?"
    args.append(limit)
    with connect() as conn:
        return [dict(row) for row in conn.execute(sql, args)]


def fault_events(machine_id: Optional[str] = None, limit: int = 100) -> List[dict]:
    sql = "SELECT * FROM fault_events"
    args: list = []
    if machine_id:
        sql += " WHERE machine_id = ?"
        args.append(machine_id)
    sql += " ORDER BY timestamp DESC, id DESC LIMIT ?"
    args.append(limit)
    with connect() as conn:
        return [dict(row) for row in conn.execute(sql, args)]


def clear_all() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM readings")
        conn.execute("DELETE FROM fault_events")