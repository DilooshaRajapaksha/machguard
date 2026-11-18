from typing import Dict, List, Optional

import numpy as np
from sklearn.ensemble import IsolationForest

from .schemas import Reading
from .simulator import Scenario, generate

FEATURES = [
    "discharge_pressure_bar",
    "discharge_temp_c",
    "oil_temp_c",
    "motor_current_a",
    "vibration_rms",
    "humidity_pct",
]

LIMITS = {
    "discharge_temp_c": 100.0,
    "motor_current_a": 60.0,
    "vibration_rms": 5.0,
    "humidity_pct": 85.0,
}

WINDOW = 30
WARN_WITHIN_MINUTES = 90
MIN_SLOPE_STRENGTH = 6.0
ANOMALY_SHARE_TO_WATCH = 0.6
ANOMALY_SHARE_TO_WARN = 0.9


def _row(r) -> List[float]:
    return [
        r.discharge_pressure_bar,
        r.discharge_temp_c,
        r.oil_temp_c,
        r.motor_current_a,
        r.vibration_rms if r.vibration_rms is not None else 1.2,
        r.humidity_pct if r.humidity_pct is not None else 60.0,
    ]


def train_model() -> IsolationForest:
    rows = []
    for seed in range(20):
        for r in generate(Scenario.HEALTHY, steps=200, seed=1000 + seed):
            rows.append(_row(r))
    model = IsolationForest(n_estimators=200, contamination=0.005, random_state=0)
    model.fit(np.array(rows))
    return model


MODEL = train_model()


def _trend(values: List[float], minutes: List[float]):
    x = np.array(minutes)
    y = np.array(values)
    if len(x) < 8:
        return 0.0, 0.0
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    resid = float(np.sum((y - fitted) ** 2))
    dof = len(x) - 2
    stderr = float(np.sqrt(resid / dof / np.sum((x - x.mean()) ** 2))) if dof > 0 else 0.0
    strength = abs(slope) / stderr if stderr > 1e-9 else 0.0
    return float(slope), float(strength)


def analyse(readings: List[Reading]) -> Dict:
    if len(readings) < 8:
        return {
            "status": "not_enough_data",
            "message": "Need at least 8 readings to judge the trend.",
            "anomaly_share": 0.0,
            "reasons": [],
            "trends": {},
        }

    window = readings[-WINDOW:]
    t0 = window[0].timestamp
    minutes = [(r.timestamp - t0).total_seconds() / 60.0 for r in window]

    flags = MODEL.predict(np.array([_row(r) for r in window])) == -1
    recent = flags[-5:]
    anomaly_share = float(np.mean(recent))

    reasons: List[str] = []
    trends: Dict[str, dict] = {}
    soonest: Optional[float] = None

    for name, limit in LIMITS.items():
        values = [getattr(r, name) for r in window]
        if any(v is None for v in values):
            continue
        slope, strength = _trend(values, minutes)
        current = values[-1]
        minutes_to_limit = None
        if slope > 0 and strength >= MIN_SLOPE_STRENGTH and current < limit:
            minutes_to_limit = (limit - current) / slope
        trends[name] = {
            "now": round(current, 2),
            "change_per_hour": round(slope * 60, 2),
            "limit": limit,
            "minutes_to_limit": round(minutes_to_limit, 1) if minutes_to_limit is not None else None,
        }
        if minutes_to_limit is not None and minutes_to_limit <= WARN_WITHIN_MINUTES:
            reasons.append(
                f"{name} is rising about {slope * 60:.1f} per hour and may reach "
                f"{limit:g} in about {minutes_to_limit:.0f} minutes"
            )
            soonest = minutes_to_limit if soonest is None else min(soonest, minutes_to_limit)

    if anomaly_share >= ANOMALY_SHARE_TO_WARN:
        reasons.append("The last readings look unlike a healthy machine")

    already = [n for n, lim in LIMITS.items() if getattr(window[-1], n) is not None and getattr(window[-1], n) >= lim]
    if already or window[-1].fault_code:
        status = "fault"
        message = "A limit has already been crossed. Follow the fault card."
    elif soonest is not None or anomaly_share >= ANOMALY_SHARE_TO_WARN:
        status = "warning"
        message = "Early warning: act before the machine trips."
    elif anomaly_share >= ANOMALY_SHARE_TO_WATCH:
        status = "watch"
        message = "Something looks a little unusual. Keep an eye on it."
        reasons.append("Some recent readings look unusual")
    else:
        status = "normal"
        message = "Everything looks healthy."

    return {
        "status": status,
        "message": message,
        "anomaly_share": round(anomaly_share, 2),
        "minutes_until_limit": round(soonest, 1) if soonest is not None else None,
        "reasons": reasons,
        "trends": trends,
    }