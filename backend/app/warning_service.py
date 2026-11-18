from datetime import datetime, timezone
from typing import Optional

from . import ai, codes
from .notification_schemas import (
    MachineWarningOut,
    MaintenanceSuggestion,
    ReadingSource,
)
from .schemas import Reading


FIELD_LABELS = {
    "discharge_temp_c": "Discharge temperature",
    "motor_current_a": "Motor current",
    "vibration_rms": "Vibration",
    "humidity_pct": "Humidity",
}

SAMPLE_CARDS = {
    "discharge_temp_c": "SAMPLE-01",
    "motor_current_a": "SAMPLE-03",
    "vibration_rms": "SAMPLE-05",
    "humidity_pct": "SAMPLE-06",
}

STATUS_MESSAGES = {
    "normal": "No warning detected in the available readings.",
    "watch": "Some readings are unusual. Review the recent measurements.",
    "warning": "Early warning detected. Review the reasons and suggested checks.",
    "fault": "A configured limit was reached or a fault code was reported.",
    "not_enough_data": "At least 8 distinct reading timestamps are needed for trend analysis.",
}


def build_suggestions(
    card_codes: list[str],
) -> list[MaintenanceSuggestion]:
    suggestions = []

    for code in dict.fromkeys(card_codes):
        card = codes.get_card(code)

        if card is None:
            continue

        steps = "\n".join(
            f"{index}. {step}"
            for index, step in enumerate(card.fix_steps, start=1)
        )

        suggestions.append(
            MaintenanceSuggestion(
                title=card.title,
                description=steps or card.meaning,
                fault_code=card.code,
                is_sample=card.is_sample,
                safety_note=card.safety_note,
            )
        )

    return suggestions


def build_warning(
    machine_id: str,
    readings: list[Reading],
    source: ReadingSource = "unknown",
    now: Optional[datetime] = None,
    stale_after_seconds: int = 300,
) -> MachineWarningOut:
    if source not in ("simulated", "measured", "unknown"):
        raise ValueError("Invalid reading source.")

    if stale_after_seconds <= 0:
        raise ValueError("The stale-data timeout must be positive.")

    if any(reading.machine_id != machine_id for reading in readings):
        raise ValueError("All readings must belong to the selected machine.")

    result = MachineWarningOut(
        machine_id=machine_id,
        status="no_data",
        message="No readings are available for this machine.",
        source=source,
    )

    if not readings:
        return result

    timestamps_have_timezone = [
        reading.timestamp.utcoffset() is not None
        for reading in readings
    ]

    if any(timestamps_have_timezone) and not all(timestamps_have_timezone):
        raise ValueError("Do not mix timestamps with and without time zones.")

    if source == "measured" and not all(timestamps_have_timezone):
        raise ValueError("Measured readings must include a timestamp time zone.")

    unique_readings = {
        reading.timestamp: reading
        for reading in readings
    }

    ordered = sorted(
        unique_readings.values(),
        key=lambda reading: reading.timestamp,
    )

    window = ordered[-ai.WINDOW:]
    latest = window[-1]

    result.latest_reading_at = latest.timestamp
    result.readings_used = len(window)

    if source != "simulated":
        if latest.timestamp.utcoffset() is None:
            result.status = "not_enough_data"
            result.message = "The reading time zone is unknown. Data freshness cannot be verified."
            return result

        current_time = now or datetime.now(timezone.utc)

        if current_time.utcoffset() is None:
            raise ValueError("The current time must include a time zone.")

        age_seconds = (
            current_time - latest.timestamp
        ).total_seconds()

        if age_seconds < -60:
            result.status = "not_enough_data"
            result.message = "The latest reading is in the future. Check the device clock."
            return result

        if age_seconds > stale_after_seconds:
            result.status = "stale"
            result.message = "The latest reading is too old to describe the current machine condition."
            result.reasons = [
                f"The latest reading is approximately {int(age_seconds)} seconds old."
            ]
            return result

    analysis = ai.analyse(window)

    result.status = analysis["status"]
    result.message = STATUS_MESSAGES[result.status]
    result.reasons = list(analysis.get("reasons", []))
    result.anomaly_share = (
        analysis.get("anomaly_share")
        if len(window) >= 8
        else None
    )
    result.minutes_until_limit = analysis.get("minutes_until_limit")

    selected_cards = []

    for field, limit in ai.LIMITS.items():
        value = getattr(latest, field)

        if value is None:
            continue

        if value >= limit:
            result.status = "fault"
            result.message = STATUS_MESSAGES["fault"]
            result.reasons.append(
                f"{FIELD_LABELS[field]} is {value:.2f}; "
                f"the configured limit is {limit:g}."
            )
            selected_cards.append(SAMPLE_CARDS[field])
            continue

        trend = analysis.get("trends", {}).get(field, {})
        minutes = trend.get("minutes_to_limit")

        if minutes is not None and 0 <= minutes <= ai.WARN_WITHIN_MINUTES:
            selected_cards.append(SAMPLE_CARDS[field])

    if latest.fault_code:
        result.status = "fault"
        result.message = STATUS_MESSAGES["fault"]
        result.reasons.append(
            f"Reported fault code: {latest.fault_code}."
        )
        selected_cards.append(latest.fault_code)

    if result.status == "fault":
        result.minutes_until_limit = None

    result.suggestions = build_suggestions(selected_cards)

    if result.status in ("watch", "warning", "fault") and not result.suggestions:
        result.suggestions = [
            MaintenanceSuggestion(
                title="Review the measurements",
                description=(
                    "Check sensor validity and compare readings at a similar "
                    "machine speed and load. Ask the responsible engineer to "
                    "review the issue using the approved equipment manual."
                ),
                is_sample=True,
                safety_note=(
                    "This is prototype guidance, not a confirmed diagnosis "
                    "or an instruction to operate the equipment."
                ),
            )
        ]

    return result