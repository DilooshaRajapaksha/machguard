# MachGuard

**Explains every fault. Warns before it happens.**

MachGuard by NovaFodge: AI fault guidance and early warning for Kaeser Sigma Control 2 compressors (TransitionX 2026, Colombo Dockyard).

## The problem
Staff at the dockyard check compressor fault codes by hand from their logs. It is slow, it depends on someone being near the machine, and a code only appears after something has already gone wrong.

## What MachGuard does
1. Reads sensor data (ESP32) and, where the dockyard allows it, the controller's own data.
2. Explains each fault code in plain words and walks the technician through the fix.
3. Warns before a failure by spotting slow changes in temperature, vibration and current.
4. Shows everything on a phone-friendly dashboard, with Telegram alerts.

## Status (28 Oct 2026)
| Part | Status |
| --- | --- |
| Data forms (schemas) | Done |
| Backend API (FastAPI) | In progress |
| Fault code dictionary | In progress (sample cards until we get the official manual) |
| Simulator and early warning | Not started |
| ESP32 sensor node | Not started |
| Web dashboard | Not started |

## Tech stack
Python, FastAPI, Pydantic, SQLite, scikit-learn, React, ESP32 (Arduino framework), MQTT.

## Folder map
```
backend/    FastAPI server, data forms, fault code dictionary
frontend/   web dashboard (React)
edge/       ESP32 firmware
simulator/  pretend compressor for testing
ml/         early-warning model
data/       public datasets for testing
docs/       diagrams and evidence
private/    never uploaded (ignored by Git)
```

## Run the backend
```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Then open http://127.0.0.1:8000/docs

## Notes
- Cards marked SAMPLE are examples of common compressor problems, not official Kaeser codes.
- MachGuard is read-only. It never sends commands to the compressor.
- Dockyard material is kept out of this repository.

## Team
NovaFodge, SLIIT