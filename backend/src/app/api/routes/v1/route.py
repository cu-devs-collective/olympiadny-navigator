import hashlib
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import DbSessionDep
from app.api.errors import ApiError
from app.db.models.route import LoginSession, Reminder, Student, new_id
from app.route.auth import describe_user, issue_session, validate_init_data
from app.route.catalog import OLYMPIADS, PROGRAMS
from app.route.schemas import (
    Catalog,
    DemoEvent,
    LoginRequest,
    Me,
    Notification,
    NotificationAction,
    NotificationList,
    Ok,
    Profile,
    SessionResponse,
    TrackResponse,
    TrackUpdate,
)
from app.route.service import (
    act_on_notification,
    add_track,
    change_track,
    create_demo_event,
    delete_profile,
    describe_notification,
    list_track,
    save_profile,
)


router = APIRouter(tags=["route"])
bearer = HTTPBearer(auto_error=False)


async def current_user(
    db: DbSessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Student:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise ApiError(401, "unauthorized", "Войдите через MAX или откройте демо")
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    session = await db.get(LoginSession, token_hash)
    if not session or session.expires_at <= time.time():
        raise ApiError(401, "session_expired", "Сессия закончилась. Войдите заново")
    user = await db.get(Student, session.user_id)
    if not user:
        raise ApiError(401, "session_expired", "Профиль удалён. Войдите заново")
    return user


UserDep = Annotated[Student, Depends(current_user)]


@router.get("/catalog", response_model=Catalog, operation_id="getCatalog")
async def catalog(request: Request) -> Catalog:
    settings = request.app.state.settings
    username = settings.bot.username if settings.bot else ""
    return Catalog(
        programs=PROGRAMS,
        olympiads=OLYMPIADS,
        demo_enabled=settings.demo_enabled,
        bot_url=f"https://max.ru/{username}" if username else None,
    )


@router.post("/auth/max", response_model=SessionResponse, operation_id="loginMax")
async def login_max(body: LoginRequest, db: DbSessionDep, request: Request) -> SessionResponse:
    settings = request.app.state.settings
    if not settings.bot:
        raise ApiError(503, "bot_unconfigured", "Вход через MAX пока не настроен")
    max_id = validate_init_data(
        body.init_data, settings.bot.token.get_secret_value(), settings.init_data_ttl_seconds
    )
    user_id = f"max:{max_id}"
    user = await db.get(Student, user_id)
    if not user:
        user = Student(id=user_id, max_user_id=max_id, profile={})
        db.add(user)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            user = await db.get(Student, user_id)
            if user is None:
                raise
    return await issue_session(db, user, settings)


@router.post("/auth/demo", response_model=SessionResponse, operation_id="loginDemo")
async def login_demo(db: DbSessionDep, request: Request) -> SessionResponse:
    settings = request.app.state.settings
    if not settings.demo_enabled:
        raise ApiError(403, "demo_disabled", "Демонстрационный вход отключён")
    user = Student(id=f"demo:{new_id()}", profile={})
    db.add(user)
    await db.flush()
    return await issue_session(db, user, settings)


@router.get("/me", response_model=Me, operation_id="getMe")
async def me(user: UserDep) -> Me:
    return describe_user(user)


@router.put("/me", response_model=Me, operation_id="saveProfile")
async def profile(body: Profile, user: UserDep, db: DbSessionDep) -> Me:
    return describe_user(await save_profile(db, user.id, body))


@router.delete("/me", response_model=Ok, operation_id="deleteProfile")
async def remove_profile(user: UserDep, db: DbSessionDep) -> Ok:
    await delete_profile(db, user.id)
    return Ok()


@router.get("/track", response_model=TrackResponse, operation_id="getTrack")
async def track(user: UserDep, db: DbSessionDep) -> TrackResponse:
    return await list_track(db, user.id)


@router.put("/track/{olympiad_id}", response_model=TrackResponse, operation_id="addToTrack")
async def add(olympiad_id: str, user: UserDep, db: DbSessionDep) -> TrackResponse:
    return await add_track(db, user.id, olympiad_id)


@router.patch("/track/{olympiad_id}", response_model=TrackResponse, operation_id="updateTrack")
async def change(
    olympiad_id: str, body: TrackUpdate, user: UserDep, db: DbSessionDep
) -> TrackResponse:
    return await change_track(db, user.id, olympiad_id, body.status)


@router.delete("/track/{olympiad_id}", response_model=TrackResponse, operation_id="removeFromTrack")
async def remove(olympiad_id: str, user: UserDep, db: DbSessionDep) -> TrackResponse:
    return await change_track(db, user.id, olympiad_id, None)


@router.get("/notifications", response_model=NotificationList, operation_id="getNotifications")
async def notifications(user: UserDep, db: DbSessionDep) -> NotificationList:
    jobs = await db.scalars(
        select(Reminder)
        .where(Reminder.user_id == user.id)
        .order_by(Reminder.due_at.desc())
        .limit(100)
    )
    return NotificationList(items=[describe_notification(job) for job in jobs])


@router.post("/demo/events", response_model=Notification, operation_id="createDemoEvent")
async def demo_event(
    body: DemoEvent, user: UserDep, db: DbSessionDep, request: Request
) -> Notification:
    if not request.app.state.settings.demo_enabled:
        raise ApiError(403, "demo_disabled", "Тестовые события отключены")
    return describe_notification(await create_demo_event(db, user.id, body.olympiad_id, body.kind))


@router.post(
    "/notifications/{notification_id}/actions", response_model=Ok, operation_id="actOnNotification"
)
async def action(
    notification_id: str, body: NotificationAction, user: UserDep, db: DbSessionDep
) -> Ok:
    await act_on_notification(db, user.id, notification_id, body.action)
    return Ok()
