import random
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, Query

from .schemas import Reading


class Scenario(str, Enum):
    HEALTHY = "healthy"
    SLOW_OVERHEATING = "slow_overheating"
    BEARING_WEAR = "bearing_wear"
    SUDDEN_FAULT = "sudden_fault"
    HUMID_DAY = "humid_day"


DESCRIPTIONS = {
    Scenario.HEALTHY: "A normal day. Everything stays steady.",
    Scenario.SLOW_OVERHEATING: "Temperature creeps up slowly. The fault code only appears near the end.",
    Scenario.BEARING_WEAR: "Vibration grows more and more, like a bearing wearing out.",
    Scenario.SUDDEN_FAULT: "Fine for a while, then the temperature and current jump suddenly.",
    Scenario.HUMID_DAY: "Salty, damp sea air builds up, so the rust risk rises.",
}

# What a healthy compressor looks like
NORMAL = {
    "pressure": 7.5,    # bar
    "temp": 80.0,       # discharge temperature, C
    "oil": 70.0,        # oil temperature, C
    "current": 45.0,    # motor current, A
    "vibration": 1.2,   # RMS
    "humidity": 60.0,   # percent
}

# How much each number wobbles by itself, like a real sensor
NOISE = {"pressure": 0.05, "temp": 0.8, "oil": 0.8, "current": 0.6,
         "vibration": 0.05, "humidity": 1.5}


def _fault_code(temp: float, current: float, vibration: float, humidity: float) -> Optional[str]:
    """Like the real controller: raise a code only once a limit is crossed."""
    if temp >= 100:
        return "SAMPLE-01"   # discharge temperature too high
    if current >= 60:
        return "SAMPLE-03"   # motor current too high
    if vibration >= 5.0:
        return "SAMPLE-05"   # vibration higher than normal
    if humidity >= 85:
        return "SAMPLE-06"   # humidity and rust risk high
    return None


def generate(
    scenario: Scenario,
    steps: int = 120,
    seed: int = 42,
    interval_s: int = 60,
    machine_id: str = "compressor-1",
    start: Optional[datetime] = None,
) -> List[Reading]:
    """Make a list of pretend readings, one every interval_s seconds."""
    rng = random.Random(seed)          # same seed = same story every time
    start = start or datetime.now()
    readings = []
    latched = None                     # a real controller keeps a fault until someone resets it

    for i in range(steps):
        p = i / max(steps - 1, 1)      # progress through the story: 0.0 to 1.0
        v = dict(NORMAL)

        if scenario == Scenario.SLOW_OVERHEATING:
            v["temp"] += 30 * p
            v["oil"] += 20 * p
            v["current"] += 4 * p
        elif scenario == Scenario.BEARING_WEAR:
            v["vibration"] += 5.3 * p ** 2
            v["current"] += 3 * p
            v["temp"] += 6 * p
        elif scenario == Scenario.SUDDEN_FAULT and p >= 0.7:
            v["temp"] += 28
            v["current"] += 22
            v["oil"] += 10
            v["pressure"] -= 0.8
        elif scenario == Scenario.HUMID_DAY:
            v["humidity"] += 35 * p

        for k in v:                    # add the sensor wobble
            v[k] += rng.gauss(0, NOISE[k])

        temp = round(min(max(v["temp"], -20), 150), 2)
        oil = round(min(max(v["oil"], -20), 150), 2)
        current = round(min(max(v["current"], 0), 500), 2)
        vibration = round(max(v["vibration"], 0), 2)
        humidity = round(min(max(v["humidity"], 0), 100), 2)
        pressure = round(min(max(v["pressure"], 0), 20), 2)

        latched = latched or _fault_code(temp, current, vibration, humidity)

        readings.append(Reading(
            machine_id=machine_id,
            timestamp=start + timedelta(seconds=i * interval_s),
            discharge_pressure_bar=pressure,
            discharge_temp_c=temp,
            oil_temp_c=oil,
            motor_current_a=current,
            vibration_rms=vibration,
            humidity_pct=humidity,
            fault_code=latched,
        ))
    return readings


router = APIRouter(prefix="/simulator", tags=["simulator"])


@router.get("/scenarios")
def scenarios():
    """The stories the pretend compressor can act out."""
    return [{"name": s.value, "description": DESCRIPTIONS[s]} for s in Scenario]


@router.get("/run", response_model=List[Reading])
def run(
    scenario: Scenario = Scenario.HEALTHY,
    steps: int = Query(120, ge=1, le=2000),
    seed: int = 42,
    interval_s: int = Query(60, ge=1, le=3600),
):
    """Act out one story and return all the readings."""
    return generate(scenario, steps=steps, seed=seed, interval_s=interval_s)