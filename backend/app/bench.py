from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import db, security


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
        conn.execute("CREATE TABLE IF NOT EXISTS bench_samples (id INTEGER PRIMARY KEY, received_at TEXT NOT NULL, sample TEXT NOT NULL)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bench_received ON bench_samples(received_at)")


def save_sample(sample):
    stamp = datetime.now(timezone.utc).isoformat()
    with db.connect() as conn:
        conn.execute("INSERT INTO bench_samples(received_at,sample) VALUES(?,?)", (stamp, sample.model_dump_json()))
    return stamp


router = APIRouter(prefix="/bench", dependencies=[Depends(security.current_user)])


@router.get("/history")
def history():
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT received_at, sample FROM bench_samples WHERE received_at >= ? ORDER BY received_at DESC, id DESC",
            (cutoff,),
        ).fetchall()
    return [{"received_at": row["received_at"], **BenchSample.model_validate_json(row["sample"]).model_dump()} for row in rows]


@router.get("/latest")
def latest():
    with db.connect() as conn:
        row = conn.execute("SELECT received_at,sample FROM bench_samples ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return None
    return {"received_at": row["received_at"], **BenchSample.model_validate_json(row["sample"]).model_dump()}
