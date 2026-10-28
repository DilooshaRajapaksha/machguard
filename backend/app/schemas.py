from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Urgency(str, Enum):
    """How quickly someone must act."""
    INFO = "info"        # just good to know
    WARNING = "warning"  # fix soon
    STOP = "stop"        # stop the machine now


class Reading(BaseModel):
    """One 'form' the compressor fills in every few seconds."""
    machine_id: str = Field(..., examples=["compressor-1"])
    timestamp: datetime = Field(default_factory=datetime.now)
    discharge_pressure_bar: float = Field(..., ge=0, le=20)
    discharge_temp_c: float = Field(..., ge=-20, le=150)
    oil_temp_c: float = Field(..., ge=-20, le=150)
    motor_current_a: float = Field(..., ge=0, le=500)
    vibration_rms: Optional[float] = Field(default=None, ge=0)
    humidity_pct: Optional[float] = Field(default=None, ge=0, le=100)
    fault_code: Optional[str] = None


class FaultCard(BaseModel):
    """A 'recipe card' that explains one fault code."""
    code: str
    title: str
    meaning: str
    likely_causes: List[str]
    fix_steps: List[str]
    urgency: Urgency
    safety_note: Optional[str] = None
    is_sample: bool = True  # True until we copy it from the real manual
