from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class Source(BaseModel):
    url: str
    title: str
    checked_at: str = "2026-09-30"
    note: str = ""


class Program(BaseModel):
    id: str
    name: str
    short_name: str
    university: str = "НИУ ВШЭ"
    campus: str = "Москва"
    description: str


class Benefit(BaseModel):
    program_id: str
    admission_year: int = 2026
    kind: Literal["bvi", "100", "unknown"]
    result: str
    diploma_grades: list[int] = Field(default_factory=list)
    confirmation: str
    explanation: str
    source: Source


class Event(BaseModel):
    id: str
    title: str
    kind: Literal["registration", "stage"]
    starts_at: str | None = None
    deadline: str | None = None
    source: Source


class Olympiad(BaseModel):
    id: str
    name: str
    profile: str
    subject: Literal["math", "informatics"]
    kind: Literal["vsosh", "listed"]
    season: str = "2026/27"
    grades: list[int]
    description: str
    registration_url: str
    source: Source
    benefits: list[Benefit]
    events: list[Event]
    level: str = "Уточняется для сезона 2026/27"


class Catalog(BaseModel):
    programs: list[Program]
    olympiads: list[Olympiad]
    snapshot_date: str = "2026-09-30"
    notice: str = "Правила приёма 2026 года — ориентир. Условия вашего года нужно проверить заново."
    demo_enabled: bool
    bot_url: str | None = None


class Profile(BaseModel):
    grade: int = Field(default=10, ge=9, le=11)
    admission_year: int = Field(default=2028, ge=2026, le=2035)
    subjects: list[Literal["math", "informatics"]] = Field(
        default_factory=lambda: ["math", "informatics"], min_length=1, max_length=2
    )
    program_ids: list[str] = Field(default_factory=list, max_length=2)
    timezone: str = "Europe/Moscow"
    notifications_enabled: bool = False
    quiet_start: int = Field(default=22, ge=0, le=23)
    quiet_end: int = Field(default=8, ge=0, le=23)
    consent: bool = False

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Укажите существующий часовой пояс") from exc
        return value

    @field_validator("program_ids", "subjects")
    @classmethod
    def unique_values(cls, value: list) -> list:
        if len(value) != len(set(value)):
            raise ValueError("Значения не должны повторяться")
        return value


class Me(BaseModel):
    id: str
    is_demo: bool
    profile: Profile


class LoginRequest(BaseModel):
    init_data: str = Field(min_length=1, max_length=16384)


class SessionResponse(BaseModel):
    token: str
    expires_at: float
    user: Me


class TrackEntry(BaseModel):
    olympiad_id: str
    status: Literal["planned", "registered", "completed"]
    added_at: float


class TrackResponse(BaseModel):
    items: list[TrackEntry]


class TrackUpdate(BaseModel):
    status: Literal["planned", "registered", "completed"]


class Notification(BaseModel):
    id: str
    olympiad_id: str
    kind: str
    state: str
    due_at: float
    deadline: float
    is_demo: bool
    sent_at: float | None
    title: str
    text: str
    error: str | None


class NotificationList(BaseModel):
    items: list[Notification]


class DemoEvent(BaseModel):
    olympiad_id: str
    kind: Literal["registration", "rule_change"] = "registration"


class NotificationAction(BaseModel):
    action: Literal["registered", "snooze", "remove", "read"]


class Ok(BaseModel):
    ok: bool = True
