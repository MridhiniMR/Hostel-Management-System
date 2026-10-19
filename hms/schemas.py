from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_identifier(value: str) -> str:
    value = value.strip()
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError("Use 1–32 letters, digits, hyphens, or underscores; the first character must be alphanumeric.")
    return value


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("identifier")
    @classmethod
    def trim_identifier(cls, value: str) -> str:
        return value.strip()


class UserSummary(BaseModel):
    username: str
    role: Literal["ADMIN", "STUDENT"]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary


class StudentCreate(BaseModel):
    student_id: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=24)
    department: str | None = Field(default=None, max_length=100)
    year_of_study: int | None = Field(default=None, ge=1, le=8)
    account_username: str | None = Field(default=None, max_length=64)

    @field_validator("student_id")
    @classmethod
    def student_id_format(cls, value: str) -> str:
        return validate_identifier(value)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required.")
        return value

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not _EMAIL.fullmatch(value):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("phone", "department")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("account_username")
    @classmethod
    def trim_account_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class StudentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=24)
    department: str | None = Field(default=None, max_length=100)
    year_of_study: int | None = Field(default=None, ge=1, le=8)
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        return self

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank.")
        return value

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not _EMAIL.fullmatch(value):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("phone", "department")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_id: str
    name: str
    email: str | None
    phone: str | None
    department: str | None
    year_of_study: int | None
    created_at: datetime
    updated_at: datetime


class RoomCreate(BaseModel):
    room_id: str = Field(min_length=1, max_length=32)
    capacity: int = Field(ge=1, le=1000)

    @field_validator("room_id")
    @classmethod
    def room_id_format(cls, value: str) -> str:
        return validate_identifier(value)


class RoomUpdate(BaseModel):
    capacity: int = Field(ge=1, le=1000)


class RoomResponse(BaseModel):
    room_id: str
    capacity: int
    occupied: int
    available: int


class AllocationCreate(BaseModel):
    student_id: str = Field(min_length=1, max_length=32)
    room_id: str = Field(min_length=1, max_length=32)

    @field_validator("student_id", "room_id")
    @classmethod
    def id_format(cls, value: str) -> str:
        return validate_identifier(value)


class AllocationUpdate(BaseModel):
    room_id: str = Field(min_length=1, max_length=32)

    @field_validator("room_id")
    @classmethod
    def id_format(cls, value: str) -> str:
        return validate_identifier(value)


class AllocationResponse(BaseModel):
    allocation_id: int
    student_id: str
    room_id: str
    status: Literal["ACTIVE", "DEALLOCATED"]
    created_at: datetime
    updated_at: datetime
    deallocated_at: datetime | None


class AuditEventResponse(BaseModel):
    event_id: int
    actor_identifier: str | None
    event_type: str
    timestamp: datetime
    outcome: str
    details: dict
