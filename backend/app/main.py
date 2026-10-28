from typing import List

from fastapi import FastAPI, HTTPException

from . import codes, simulator
from .schemas import FaultCard

app = FastAPI(
    title="MachGuard API",
    description="Fault guidance and early warning for Kaeser Sigma Control 2 compressors",
    version="0.3.0",
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