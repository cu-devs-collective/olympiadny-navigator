import datetime as dt
import time
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError
from app.db.models.route import LoginSession, Reminder, Student, TrackItem, new_id
from app.route.catalog import PROGRAMS, get_olympiad
from app.route.schemas import Notification, Profile, TrackEntry, TrackResponse


async def lock_student(db: AsyncSession, user_id: str) -> Student:
    # Serializes track/profile/outbox mutations for one user on PostgreSQL.
    user = await db.scalar(
        select(Student)
        .where(Student.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None:
        raise ApiError(401, "session_expired", "Войдите в приложение заново")
    return user


async def list_track(db: AsyncSession, user_id: str) -> TrackResponse:
    items = await db.scalars(
        select(TrackItem).where(TrackItem.user_id == user_id).order_by(TrackItem.created_at)
    )
    return TrackResponse(
        items=[
            TrackEntry.model_validate(
                {"olympiad_id": i.olympiad_id, "status": i.status, "added_at": i.created_at}
            )
            for i in items
        ]
    )


async def sync_reminders(db: AsyncSession, user: Student) -> None:
    """Reconcile future reminders; never resend a delivered or ambiguous job."""
    profile = Profile(**user.profile)
    items = list(await db.scalars(select(TrackItem).where(TrackItem.user_id == user.id)))
    jobs = list(await db.scalars(select(Reminder).where(Reminder.user_id == user.id)))
    existing = {j.dedup_key: j for j in jobs}
    valid = set()
    now = time.time()
    if profile.notifications_enabled:
        for item in items:
            if item.status == "completed":
                continue
            olympiad = get_olympiad(item.olympiad_id)
            for event in olympiad.events:
                if not event.deadline or (
                    event.kind == "registration" and item.status != "planned"
                ):
                    continue
                # A stage reminder makes sense only after the student's registration.
                if event.kind == "stage" and item.status != "registered":
                    continue
                deadline = dt.datetime.fromisoformat(event.deadline).timestamp()
                for days in (7, 1):
                    due = deadline - days * 86400
                    key = f"{item.id}:{event.id}:{event.deadline}:{days}"
                    if deadline <= now:
                        continue
                    valid.add(key)
                    if key in existing and existing[key].state == "cancelled" and due > now:
                        # /resume restores only unsent future jobs that are relevant again.
                        existing[key].state = "pending"
                        existing[key].due_at = due
                    if key not in existing and due > now:
                        db.add(
                            Reminder(
                                user_id=user.id,
                                olympiad_id=olympiad.id,
                                dedup_key=key,
                                kind=event.kind,
                                due_at=due,
                                deadline=deadline,
                                content={
                                    "title": f"{olympiad.name} · {olympiad.profile}",
                                    "text": f"{event.title}. Срок: {event.deadline}. "
                                    f"Проверьте условия: {event.source.url}",
                                },
                            )
                        )
    for job in jobs:
        if job.state == "pending" and not job.is_demo and job.dedup_key not in valid:
            job.state = "cancelled"
        if job.state == "pending" and not profile.notifications_enabled:
            job.state = "cancelled"


async def save_profile(db: AsyncSession, user_id: str, profile: Profile) -> Student:
    if not profile.consent:
        raise ApiError(
            422, "consent_required", "Для сохранения нужно согласие на обработку профиля"
        )
    known = {p.id for p in PROGRAMS}
    if not profile.program_ids or not set(profile.program_ids) <= known:
        raise ApiError(422, "invalid_programs", "Выберите хотя бы одну программу из каталога")
    user = await lock_student(db, user_id)
    user.profile = profile.model_dump()
    await sync_reminders(db, user)
    await db.commit()
    return user


async def add_track(db: AsyncSession, user_id: str, olympiad_id: str) -> TrackResponse:
    olympiad = get_olympiad(olympiad_id)
    user = await lock_student(db, user_id)
    profile = Profile(**user.profile)
    if not profile.consent or not profile.program_ids:
        raise ApiError(409, "profile_required", "Сначала сохраните профиль и выберите цель")
    if profile.grade not in olympiad.grades:
        raise ApiError(422, "grade_unavailable", "Этот профиль не доступен для вашего класса")
    item = await db.scalar(
        select(TrackItem).where(TrackItem.user_id == user_id, TrackItem.olympiad_id == olympiad_id)
    )
    if item is None:
        db.add(TrackItem(user_id=user_id, olympiad_id=olympiad_id))
        await db.flush()
    await sync_reminders(db, user)
    await db.commit()
    return await list_track(db, user_id)


async def change_track(
    db: AsyncSession, user_id: str, olympiad_id: str, status: str | None
) -> TrackResponse:
    user = await lock_student(db, user_id)
    item = await db.scalar(
        select(TrackItem).where(TrackItem.user_id == user_id, TrackItem.olympiad_id == olympiad_id)
    )
    if item is None:
        raise ApiError(404, "track_not_found", "Олимпиада уже удалена из вашего трека")
    if status is None:
        await db.delete(item)
    else:
        item.status = status
    # Cancel reminders made obsolete by the action, including demonstration jobs.
    jobs = await db.scalars(
        select(Reminder).where(
            Reminder.user_id == user_id,
            Reminder.olympiad_id == olympiad_id,
            Reminder.state == "pending",
        )
    )
    for job in jobs:
        if (
            status is None
            or status == "completed"
            or (status == "registered" and job.kind == "registration")
        ):
            job.state = "cancelled"
    await db.flush()
    await sync_reminders(db, user)
    await db.commit()
    return await list_track(db, user_id)


def describe_notification(job: Reminder) -> Notification:
    return Notification(
        id=job.id,
        olympiad_id=job.olympiad_id,
        kind=job.kind,
        state=job.state,
        due_at=job.due_at,
        deadline=job.deadline,
        is_demo=job.is_demo,
        sent_at=job.sent_at,
        title=job.content["title"],
        text=job.content["text"],
        error=job.error,
    )


async def create_demo_event(
    db: AsyncSession, user_id: str, olympiad_id: str, kind: str
) -> Reminder:
    user = await lock_student(db, user_id)
    profile = Profile(**user.profile)
    if not profile.notifications_enabled:
        raise ApiError(409, "notifications_disabled", "Сначала включите напоминания в профиле")
    item = await db.scalar(
        select(TrackItem).where(TrackItem.user_id == user_id, TrackItem.olympiad_id == olympiad_id)
    )
    if not item:
        raise ApiError(409, "track_required", "Сначала добавьте олимпиаду в трек")
    if kind == "registration" and item.status != "planned":
        raise ApiError(409, "already_registered", "Вы уже отметили регистрацию на эту олимпиаду")
    now = time.time()
    recent = await db.scalar(
        select(Reminder).where(
            Reminder.user_id == user_id, Reminder.is_demo.is_(True), Reminder.due_at > now - 30
        )
    )
    if recent:
        raise ApiError(429, "demo_cooldown", "Следующее тестовое событие доступно через 30 секунд")
    olympiad = get_olympiad(olympiad_id)
    text = (
        "Тест: регистрация на демонстрационное событие заканчивается завтра. "
        "Настоящие сроки олимпиады не менялись."
        if kind == "registration"
        else "Тест изменения: в модельном правиле добавлено подтверждение ЕГЭ. "
        "Это пример уведомления, а не изменение реальных правил вуза. "
        "Откройте карточку и проверьте источник перед пересмотром маршрута."
    )
    job = Reminder(
        id=new_id(),
        user_id=user_id,
        olympiad_id=olympiad_id,
        dedup_key=f"demo:{new_id()}",
        kind=kind,
        due_at=now,
        deadline=now + 86400,
        state="preview" if user.max_user_id is None else "pending",
        is_demo=True,
        content={"title": f"ТЕСТ · {olympiad.name} · {olympiad.profile}", "text": text},
    )
    db.add(job)
    await db.commit()
    return job


async def act_on_notification(db: AsyncSession, user_id: str, job_id: str, action: str) -> None:
    user = await lock_student(db, user_id)
    job = await db.scalar(
        select(Reminder).where(Reminder.id == job_id, Reminder.user_id == user_id)
    )
    if not job:
        raise ApiError(404, "notification_not_found", "Уведомление не найдено")
    item = await db.scalar(
        select(TrackItem).where(
            TrackItem.user_id == user_id, TrackItem.olympiad_id == job.olympiad_id
        )
    )
    if item is None:
        raise ApiError(409, "track_removed", "Олимпиада уже удалена из трека")
    if action == "registered":
        if job.kind != "registration":
            raise ApiError(422, "wrong_action", "Это уведомление не о регистрации")
        if item.status == "completed":
            raise ApiError(409, "already_completed", "Участие уже завершено")
        await change_track(db, user_id, job.olympiad_id, "registered")
        job.state = "read"
        await db.commit()
    elif action == "remove":
        await change_track(db, user_id, job.olympiad_id, None)
    elif action == "snooze":
        if not Profile(**user.profile).notifications_enabled:
            raise ApiError(409, "notifications_disabled", "Напоминания отключены")
        if item.status != "planned" and job.kind == "registration":
            raise ApiError(409, "already_registered", "Регистрация уже отмечена")
        if job.deadline <= time.time() + 3600:
            raise ApiError(
                409, "deadline_too_close", "До срока меньше часа: откройте событие сейчас"
            )
        if job.state not in {"sent", "preview"}:
            raise ApiError(409, "already_handled", "Напоминание уже обработано")
        job.due_at = time.time() + 3600
        job.state = "pending"
        await db.commit()
    else:
        job.state = "read"
        await db.commit()


async def delete_profile(db: AsyncSession, user_id: str) -> None:
    await lock_student(db, user_id)
    for model in (Reminder, TrackItem, LoginSession):
        await db.execute(delete(model).where(model.user_id == user_id))
    await db.execute(delete(Student).where(Student.id == user_id))
    await db.commit()


def quiet_until(profile: Profile, now: float) -> float | None:
    local = dt.datetime.fromtimestamp(now, ZoneInfo(profile.timezone))
    start, end = profile.quiet_start, profile.quiet_end
    if start == end:
        return None
    quiet = start <= local.hour < end if start < end else local.hour >= start or local.hour < end
    if not quiet:
        return None
    target = local.replace(hour=end, minute=0, second=0, microsecond=0)
    if target <= local:
        target += dt.timedelta(days=1)
    return target.timestamp()


async def stop_notifications(db: AsyncSession, user_id: str) -> None:
    user = await lock_student(db, user_id)
    user.profile = {**user.profile, "notifications_enabled": False}
    await db.execute(
        update(Reminder)
        .where(Reminder.user_id == user_id, Reminder.state == "pending")
        .values(state="cancelled")
    )
    await db.commit()
