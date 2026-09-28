"""Durable outbox worker. Only the bot process dispatches MAX messages."""

import asyncio
import time

import loguru
import maxapi
from maxapi.enums import AttachmentType
from maxapi.types import (
    Attachment,
    AttachmentUpload,
    ButtonsPayload,
    CallbackButton,
    InputMedia,
    InputMediaBuffer,
    LinkButton,
)
from sqlalchemy import select, update

from app.core.config import Settings
from app.db.connector import Database
from app.db.models.route import Reminder, Student, TrackItem
from app.route.catalog import get_olympiad
from app.route.schemas import Profile
from app.route.service import quiet_until


def route_buttons(
    username: str,
) -> list[Attachment | InputMedia | InputMediaBuffer | AttachmentUpload]:
    if not username:
        return []
    return [
        Attachment(
            type=AttachmentType.INLINE_KEYBOARD,
            payload=ButtonsPayload(
                buttons=[
                    [
                        LinkButton(
                            text="Открыть мой маршрут",
                            url=f"https://max.ru/{username}?startapp=route",
                        ),
                    ]
                ]
            ),
        )
    ]


def reminder_buttons(
    job: Reminder, username: str
) -> list[Attachment | InputMedia | InputMediaBuffer | AttachmentUpload]:
    rows: list = [
        [LinkButton(text="Сайт организатора", url=get_olympiad(job.olympiad_id).registration_url)]
    ]
    if job.kind == "registration":
        rows.append(
            [CallbackButton(text="Я зарегистрировался", payload=f"route:registered:{job.id}")]
        )
    else:
        rows.append([CallbackButton(text="Ознакомился", payload=f"route:read:{job.id}")])
    rows.append(
        [
            CallbackButton(text="Через час", payload=f"route:snooze:{job.id}"),
            CallbackButton(text="Убрать из трека", payload=f"route:remove:{job.id}"),
        ]
    )
    if username:
        rows.append(
            [
                LinkButton(
                    text="Мой маршрут и условия", url=f"https://max.ru/{username}?startapp=route"
                )
            ]
        )
    return [Attachment(type=AttachmentType.INLINE_KEYBOARD, payload=ButtonsPayload(buttons=rows))]


async def dispatch_due(
    database: Database, bot: maxapi.Bot, username: str, now: float | None = None
) -> int:
    now = time.time() if now is None else now
    sent = 0
    async with database.session_factory() as db:
        # A crashed sender may have already delivered. Do not blindly resend these jobs.
        await db.execute(
            update(Reminder)
            .where(Reminder.state == "sending", Reminder.claimed_at < now - 300)
            .values(
                state="failed", error="Отправка прервана; доставка неизвестна. Автоповтор отключён."
            )
        )
        ids = list(
            await db.scalars(
                select(Reminder.id)
                .where(Reminder.state == "pending", Reminder.due_at <= now)
                .order_by(Reminder.due_at)
                .limit(50)
            )
        )
        await db.commit()
    for job_id in ids:
        async with database.session_factory() as db:
            claimed = await db.execute(
                update(Reminder)
                .where(Reminder.id == job_id, Reminder.state == "pending")
                .values(state="sending", claimed_at=now)
                .returning(Reminder.id)
            )
            if claimed.scalar_one_or_none() is None:
                await db.rollback()
                continue
            await db.commit()
            job = await db.get(Reminder, job_id)
            if job is None:
                continue
            # Same per-user lock as profile/track changes. Opt-outs cannot be lost
            # between reading preferences and sending a notification.
            user = await db.scalar(
                select(Student).where(Student.id == job.user_id).with_for_update()
            )
            item = await db.scalar(
                select(TrackItem).where(
                    TrackItem.user_id == job.user_id, TrackItem.olympiad_id == job.olympiad_id
                )
            )
            profile = Profile(**user.profile) if user else Profile()
            obsolete = (
                not item
                or item.status == "completed"
                or (job.kind == "registration" and item.status != "planned")
                or (job.kind == "stage" and item.status != "registered")
            )
            if not user or not profile.notifications_enabled or obsolete or now >= job.deadline:
                job.state = "cancelled"
                await db.commit()
                continue
            delay = quiet_until(profile, now)
            if delay is not None:
                job.state = "pending" if delay < job.deadline else "cancelled"
                job.due_at = delay
                await db.commit()
                continue
            if user.max_user_id is None:
                job.state = "preview"
                await db.commit()
                continue
            try:
                result = await asyncio.wait_for(
                    bot.send_message(
                        user_id=user.max_user_id,
                        text=f"{job.content['title']}\n\n{job.content['text']}",
                        attachments=reminder_buttons(job, username),
                    ),
                    timeout=20,
                )
                if result is None:
                    raise RuntimeError("MAX did not confirm the request")
                job.state = "sent"
                job.sent_at = now
                sent += 1
            except Exception:
                # Do not log payloads, user data or token-bearing SDK exceptions.
                job.state = "failed"
                job.error = "MAX не подтвердил отправку. Проверьте запуск бота и подключение."
                loguru.logger.warning("Notification delivery was not confirmed: {}", job.id)
            await db.commit()
        # Enforce a conservative per-dialog rate even if all jobs target one student.
        await asyncio.sleep(0.6)
    return sent


async def notification_loop(database: Database, bot: maxapi.Bot, settings: Settings) -> None:
    username = settings.bot.username if settings.bot else ""
    while True:
        try:
            await dispatch_due(database, bot, username)
        except Exception:
            loguru.logger.error("Notification worker iteration failed; will retry pending jobs")
        await asyncio.sleep(settings.scheduler_interval_seconds)
