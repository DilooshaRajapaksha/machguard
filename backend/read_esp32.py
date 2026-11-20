import argparse
import sys

from pydantic import ValidationError

from app.bench import BenchSample, init_bench, save_sample


LABELS = {
    "Uptime": "uptime_s",
    "Surface temperature 1": "probe_c",
    "Surface temperature 2": "probe2_c",
    "Current ADC voltage": "current_adc_v",
    "Estimated motor current [uncalibrated]": "current_a",
    "Voltage ADC voltage": "voltage_adc_v",
    "Motor terminal voltage [uncalibrated]": "motor_v",
    "Acceleration variation RMS": "vibration_rms",
    "Measured sample rate": "sample_hz",
    "Sampling timing resets": "timing_resets",
    "DHT11 temperature [UNVERIFIED]": "air_c",
    "DHT11 humidity [UNVERIFIED]": "humidity_pct",
}


def usb_lines(lines):
    """Hold a text report until the firmware announces its Wi-Fi result."""
    report = []
    for raw in lines:
        line = raw.strip()
        if line.startswith("Wi-Fi upload HTTP 201"):
            report.clear()
        elif line == "--- MachGuard readings ---":
            yield from report
            report = [raw]
        elif line.startswith("{"):
            yield from report
            report = []
            yield raw
        elif report:
            if line.startswith(("Wi-Fi disconnected", "Wi-Fi upload HTTP ")):
                yield from report
                report = []
            elif len(report) < 100:
                report.append(raw)
            else:
                report = []
    yield from report


def samples(lines):
    block = None
    for raw in lines:
        line = raw.strip()
        if line == "--- MachGuard readings ---":
            block = {}
            continue
        try:
            if line.startswith("{"):
                block = None
                yield BenchSample.model_validate_json(line)
                continue
            if block is None:
                continue
            label, _, value = line.partition(":")
            if label in LABELS:
                token = value.strip().split()[0]
                block[LABELS[label]] = None if token == "DISCONNECTED" else float(token)
            elif label != "DHT11 [UNVERIFIED]":
                if line.startswith(("Stopped:", "READY:", "===")):
                    block = None
                continue
            if label in ("DHT11 humidity [UNVERIFIED]", "DHT11 [UNVERIFIED]"):
                if "motor_v" in block:
                    yield BenchSample.model_validate(block)
                block = None
        except (ValueError, IndexError, ValidationError):
            block = None
            print("Skipped incomplete or invalid sensor report.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("device", nargs="?")
    parser.add_argument("--temperature-limit", type=float)
    args = parser.parse_args()
    if args.temperature_limit is not None and (not args.device or not -55 <= args.temperature_limit <= 125):
        parser.error("Select a registered device and a probe limit between -55 and 125 C.")
    init_bench()
    for sample in samples(usb_lines(sys.stdin)):
        print(save_sample(sample, args.device, args.temperature_limit), sample.model_dump_json(exclude_none=True), flush=True)
