from fastapi import FastAPI

app = FastAPI(
    title="MechGuard API",
    description="Fault guidance and early warning for Kaeser Sigma Control 2 compressors",
    version="0.1.0",
)


@app.get("/")
def home():
    return {"app": "MachGuard", "message": "Backend is alive"}


@app.get("/health")
def health():
    return {"status": "ok"}