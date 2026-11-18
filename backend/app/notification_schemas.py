from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


AlertSeverity = Literal["info", "watch", "warning", "fault"]

ReadingSource = Literal["simulated", "measured", "unknown"]

AnalysisStatus = Literal[
    "normal",
    "watch",
    "warning",
    "fault",
    "not_enough_data",
    "no_data",
    "stale",
]


class MaintenanceSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    fault_code: Optional[str] = None
    is_sample: bool = True
    safety_note: Optional[str] = None


class NotificationCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    machine_id: str = Field(min_length=1, max_length=64)
    severity: AlertSeverity
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)
    source: ReadingSource
    reading_timestamp: datetime
    reasons: list[str] = Field(default_factory=list)
    suggestions: list[MaintenanceSuggestion] = Field(default_factory=list)


class NotificationOut(NotificationCreate):
    id: int = Field(gt=0)
    created_at: datetime
    is_read: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class NotificationList(BaseModel):
    items: list[NotificationOut] = Field(default_factory=list)
    total: int = Field(ge=0)
    unread_count: int = Field(ge=0)


class MachineWarningOut(BaseModel):
    machine_id: str
    status: AnalysisStatus
    message: str
    source: ReadingSource
    latest_reading_at: Optional[datetime] = None
    readings_used: int = Field(default=0, ge=0)
    anomaly_share: Optional[float] = Field(default=None, ge=0, le=1)
    minutes_until_limit: Optional[float] = Field(default=None, ge=0)
    reasons: list[str] = Field(default_factory=list)
    suggestions: list[MaintenanceSuggestion] = Field(default_factory=list)