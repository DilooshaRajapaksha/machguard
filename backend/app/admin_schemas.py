from typing import Optional

from pydantic import BaseModel, Field

USERNAME_PATTERN = r"^[A-Za-z0-9._-]{3,32}$"


class LoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class UserCreate(BaseModel):
    username: str = Field(..., pattern=USERNAME_PATTERN)
    full_name: str = Field(..., min_length=2, max_length=80)
    password: str
    role: str = Field("viewer", pattern="^(admin|viewer)$")


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=80)
    role: Optional[str] = Field(None, pattern="^(admin|viewer)$")
    is_active: Optional[bool] = None


class ResetPasswordIn(BaseModel):
    new_password: str