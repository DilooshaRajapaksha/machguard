from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import admin_routes, ai, auth_routes, codes, db, simulator
from .schemas import FaultCard, Reading

app = FastAPI(
    title="MachGuard API",
    description="Fault guidance and early warning for Kaeser Sigma Control 2 compressors",
    version="0.5.0",
)

db.init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulator.router)
app.include_router(auth_routes.router)
app.include_router(admin_routes.router)

@app.get("/")
def home():
    return {"app": "MachGuard", "message": "Backend is alive"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/codes", response_model=List[FaultCard])
def all_codes():
    """Every recipe card we have."""
    return codes.list_cards()


@app.get("/codes/{code}", response_model=FaultCard)
def one_code(code: str):
    """One recipe card, looked up by its code."""
    card = codes.get_card(code)
    if card is None:
        raise HTTPException(status_code=404, detail=f"No card for code '{code}'")
    return card


@app.post("/readings")
def add_reading(reading: Reading):
    """The machine (or the simulator) hands us one reading. We write it in the diary."""
    new_id = db.save_reading(reading)
    return {"saved": True, "id": new_id}


@app.get("/readings")
def get_readings(
    machine_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
):
    """Read the diary back, newest first."""
    return db.latest_readings(machine_id, limit)


@app.get("/faults")
def get_faults(
    machine_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
):
    """Every time a new fault code showed up."""
    return db.fault_events(machine_id, limit)


@app.post("/simulator/load")
def load_story(
    scenario: simulator.Scenario = simulator.Scenario.HEALTHY,
    steps: int = Query(120, ge=1, le=2000),
    seed: int = 42,
    fraction: float = Query(1.0, gt=0, le=1),
):
    """Act out a story AND write its readings into the diary. Use fraction to stop partway."""
    readings = simulator.generate(scenario, steps=steps, seed=seed)
    keep = readings[: max(1, int(steps * fraction))]
    for r in keep:
        db.save_reading(r)
    return {"saved": len(keep), "scenario": scenario.value}


@app.get("/analysis")
def analysis(machine_id: str = "compressor-1", window: int = Query(30, ge=8, le=500)):
    """Ask the AI how the machine looks right now."""
    rows = list(reversed(db.latest_readings(machine_id, window)))
    readings = [Reading(**row) for row in rows]
    result = ai.analyse(readings)
    result["machine_id"] = machine_id
    result["readings_used"] = len(readings)
    return result


@app.post("/simulator/reset")
def reset_diary():
    """Empty the diary so a demo can start from a clean page."""
    db.clear_all()
    return {"cleared": True}