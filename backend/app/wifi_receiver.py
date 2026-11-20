"""Private-LAN receiver for one provisioned bench ESP32."""
import os
import secrets

from fastapi import FastAPI, Header, HTTPException

from .bench import BenchSample, save_sample

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.post("/sample", status_code=201)
def receive(sample: BenchSample, x_device_key: str = Header(default="")):
    key = os.environ.get("ESP32_KEY", "")
    if not key or not secrets.compare_digest(key.encode(), x_device_key.encode()):
        raise HTTPException(401, "Invalid device key")
    try:
        stamp = save_sample(sample, os.environ["ESP32_DEVICE_ID"])
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"received_at": stamp}
