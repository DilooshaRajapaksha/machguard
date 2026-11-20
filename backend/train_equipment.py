import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import numpy as np
from sklearn.linear_model import LinearRegression


PROFILES = {
    "compressor": {
        "manufacturer": "KAESER",
        "controller": "SIGMA CONTROL 2",
        "panel_part": "DSDX.2",
        "panel_serial": "1928",
        "signal": "discharge_temp_c",
    },
    "generator": {
        "model": None,
        "signal": "coolant_temp_c",
    },
}


def evaluate(path, kind, machine_id):
    profile = PROFILES[kind]
    signal = profile["signal"]
    samples = {}
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = csv.DictReader(source)
        required = {"timestamp", "machine_id", signal}
        if not required.issubset(rows.fieldnames or []):
            raise ValueError("Required columns: " + ", ".join(sorted(required)))
        for row in rows:
            if row["machine_id"] != machine_id:
                continue
            stamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            if stamp.utcoffset() is None:
                raise ValueError("Include a timezone in each timestamp.")
            stamp = stamp.astimezone(timezone.utc)
            value = float(row[signal])
            if not np.isfinite(value) or stamp in samples:
                raise ValueError("Each timestamp needs one finite measurement.")
            samples[stamp] = value

    times = sorted(samples)
    if len(times) < 20:
        raise ValueError("Provide at least 20 distinct readings for this machine.")
    gaps = [(b-a).total_seconds() for a, b in zip(times, times[1:])]
    interval = median(gaps)
    features, targets = [], []
    for i in range(2, len(times)):
        if all(abs(gap-interval) <= interval*0.1 for gap in gaps[i-2:i]):
            features.append([samples[times[i-2]], samples[times[i-1]]])
            targets.append(samples[times[i]])
    if len(targets) < 15:
        raise ValueError("Too few consecutive readings at a consistent interval.")
    x, y = np.array(features), np.array(targets)
    split = len(y)*4//5
    model = LinearRegression().fit(x[:split], y[:split])
    predicted = model.predict(x[split:])
    return {
        "machine_id": machine_id, "profile": profile, "source": path.name,
        "prediction_interval_seconds": interval,
        "training_examples": split, "test_examples": len(y)-split,
        "test_mean_absolute_error_c": float(np.mean(abs(predicted-y[split:]))),
        "last_reading_mean_absolute_error_c": float(np.mean(abs(x[split:,1]-y[split:]))),
        "previous_and_latest_coefficients": model.coef_.tolist(),
        "intercept": model.intercept_,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train and evaluate a single-machine temperature forecast.")
    parser.add_argument("profile", choices=PROFILES)
    parser.add_argument("machine_id")
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(evaluate(args.csv, args.profile, args.machine_id), indent=2))
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, str(error) + "\n")
