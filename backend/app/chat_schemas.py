from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[UUID] = None
    machine_id: Optional[str] = Field(default=None, min_length=1, max_length=64)


class EnergyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    energy_kwh: float = Field(ge=0, le=1e9)
    production_units: float = Field(ge=0.000001, le=1e12)
    emission_factor: float = Field(ge=0, le=100)
    factor_source: str = Field(min_length=3, max_length=300)
