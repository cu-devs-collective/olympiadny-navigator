from datetime import datetime
from typing import Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator


SubjectId = Literal[
    "math",
    "informatics",
    "physics",
    "chemistry",
    "biology",
    "history",
    "social",
    "russian",
    "literature",
    "english",
    "geography",
    "economics",
]


class Subject(BaseModel):
    id: SubjectId
    name: str


def admission_year_for_grade(grade: int, today: datetime | None = None) -> int:
    today = today or datetime.now(ZoneInfo("Europe/Moscow"))
    # The school year begins in September. During summer use the completed grade.
    graduation_year = today.year + (1 if today.month >= 9 else 0)
    return graduation_year + 11 - grade


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
    direction: str = "01.03.02 Прикладная математика и информатика"
    url: str = "https://ba.hse.ru/"


class Benefit(BaseModel):
    program_id: str
    admission_year: int = 2026
    kind: Literal["bvi", "100", "unknown"]
    result: str
    diploma_grades: list[int] = Field(default_factory=list)
    confirmation: str
    explanation: str
    source: Source
    diploma_validity_years: int | None = None
    validity_source: Source | None = None


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
    subject: SubjectId
    kind: Literal["vsosh", "listed"]
    season: str = "2026/27"
    grades: list[int]
    description: str
    registration_url: str
    source: Source
    benefits: list[Benefit]
    events: list[Event]
    level: str = "Уточняется для сезона 2026/27"
    registry_level: Literal[1, 2, 3] | None = None
    registry_season: str | None = None
    registry_source: Source | None = None
    aliases: list[str] = Field(default_factory=list)


class Catalog(BaseModel):
    programs: list[Program]
    subjects: list[Subject]
    olympiads: list[Olympiad]
    snapshot_date: str = "2026-09-30"
    notice: str = "Данные актуальны на 30.09.2026"
    demo_enabled: bool
    bot_url: str | None = None


class Profile(BaseModel):
    grade: int = Field(default=10, ge=9, le=11)
    admission_year: int = Field(default=2028, ge=2026, le=2035)
    subjects: list[SubjectId] = Field(
        default_factory=lambda: ["math", "informatics"], min_length=1, max_length=12
    )
    program_ids: list[str] = Field(default_factory=list)
    timezone: str = "Europe/Moscow"
    notifications_enabled: bool = False
    quiet_start: int = Field(default=22, ge=0, le=23)
    quiet_end: int = Field(default=8, ge=0, le=23)
    consent: bool = False

    @model_validator(mode="after")
    def derive_admission_year(self) -> Self:
        self.admission_year = admission_year_for_grade(self.grade)
        return self

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


class ConsentRequest(BaseModel):
    accepted: Literal[True]
