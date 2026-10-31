from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from . import codes, db, simulator
from .schemas import FaultCard, Reading

app = FastAPI(
    title="MachGuard API",
    description="Fault guidance and early warning for Kaeser Sigma Control 2 compressors",
    version="0.4.0",
)

db.init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulator.router)


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
):
    """Act out a story AND write all its readings into the diary."""
    for r in simulator.generate(scenario, steps=steps, seed=seed):
        db.save_reading(r)
    return {"saved": steps, "scenario": scenario.value}