from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import db, security
from .notification_schemas import MachineWarningOut
from .notification_service import record_warning


class BenchSample(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    probe_c: float | None = Field(default=None, ge=-55, le=125)
    air_c: float | None = None
    humidity_pct: float | None = Field(default=None, ge=0, le=100)
    ax: float | None = None
    ay: float | None = None
    az: float | None = None

    probe2_c: float | None = Field(default=None, ge=-55, le=125)
    current_adc_v: float | None = None
    current_a: float | None = None
    voltage_adc_v: float | None = None
    motor_v: float | None = None
    vibration_rms: float | None = None
    sample_hz: float | None = None
    timing_resets: int | None = None
    uptime_s: int | None = None

    @model_validator(mode="after")
    def require_sensor(self):
        if all(value is None for value in self.model_dump(exclude={"uptime_s", "timing_resets", "sample_hz"}).values()):
            raise ValueError("No sensor responded")
        return self


def init_bench():
    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("CREATE TABLE IF NOT EXISTS bench_samples (id INTEGER PRIMARY KEY, received_at TEXT NOT NULL, sample TEXT NOT NULL)")
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(bench_samples)")}
        if "registry_id" not in columns:
            conn.execute("ALTER TABLE bench_samples ADD COLUMN registry_id INTEGER")
            conn.execute("ALTER TABLE bench_samples ADD COLUMN device_id TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bench_machine ON bench_samples(registry_id, received_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bench_received ON bench_samples(received_at)")


def check_temperature(conn, registry_id, stamp, limit):
    rows = conn.execute("""
        SELECT received_at, json_extract(sample, '$.probe_c') AS temperature
        FROM bench_samples WHERE registry_id=? ORDER BY id DESC LIMIT 3
    """, (registry_id,)).fetchall()
    if len(rows) < 3 or any(r["temperature"] is None for r in rows):
        return
    if datetime.fromisoformat(stamp) - datetime.fromisoformat(rows[-1]["received_at"]) > timedelta(seconds=30):
        return
    readings = [r["temperature"] for r in rows]
    if min(readings) >= limit:
        status = "fault"
    elif max(readings) < limit:
        status = "normal"
    else:
        return
    machine = conn.execute("SELECT machine_id FROM machines WHERE id=?", (registry_id,)).fetchone()
    warning = MachineWarningOut(machine_id=machine["machine_id"], status=status, source="measured",
                                latest_reading_at=stamp, readings_used=3,
                                message=f"Surface probe 1 reached {readings[0]:g} C. Configured limit: {limit:g} C.",
                                reasons=[f"Recent probe temperatures in C, newest first: {readings}"])
    record_warning(warning, stream_id="surface-probe-1", connection=conn)


def save_sample(sample, device_id=None, temperature_limit=None):
    stamp = datetime.now(timezone.utc).isoformat()
    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        registry_id = None
        if device_id:
            link = conn.execute("SELECT machine_id FROM machine_devices WHERE device_id=?", (device_id,)).fetchone()
            if link is None:
                raise ValueError(f"Register device {device_id} on the admin Machines page first.")
            registry_id = link["machine_id"]
        conn.execute("INSERT INTO bench_samples(received_at,sample,registry_id,device_id) VALUES(?,?,?,?)",
                     (stamp, sample.model_dump_json(), registry_id, device_id))
        if registry_id is not None and temperature_limit is not None:
            check_temperature(conn, registry_id, stamp, temperature_limit)
    return stamp


router = APIRouter(prefix="/bench", dependencies=[Depends(security.current_user)])


def machine_record(conn, machine_id):
    if machine_id is None:
        return None
    row = conn.execute("SELECT id FROM machines WHERE machine_id=?", (machine_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Unknown machine.")
    return row["id"]


@router.get("/history")
def history(machine_id: str | None = None, user: dict = Depends(security.current_user)):
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    with db.connect() as conn:
        registry_id = machine_record(conn, machine_id)
        if user["role"] != "admin":
            assigned = conn.execute("""
                SELECT 1 FROM machines m JOIN engineer_accounts a ON a.engineer_id=m.engineer_id
                WHERE m.id=? AND a.user_id=?
            """, (registry_id, user["id"])).fetchone()
            if assigned is None:
                raise HTTPException(403, "History is available to the assigned engineer.")
        rows = conn.execute(
            "SELECT received_at, sample FROM bench_samples WHERE registry_id IS ? AND received_at >= ? ORDER BY received_at DESC, id DESC",
            (registry_id, cutoff),
        ).fetchall()
    return [{"received_at": row["received_at"], **BenchSample.model_validate_json(row["sample"]).model_dump()} for row in rows]


@router.get("/latest")
def latest(machine_id: str | None = None):
    with db.connect() as conn:
        row = conn.execute("SELECT received_at,sample FROM bench_samples WHERE registry_id IS ? ORDER BY id DESC LIMIT 1", (machine_record(conn, machine_id),)).fetchone()
    if row is None:
        return None
    return {"received_at": row["received_at"], **BenchSample.model_validate_json(row["sample"]).model_dump()}
