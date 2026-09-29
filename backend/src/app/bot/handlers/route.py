import maxapi
from maxapi.types import BotStarted, MessageCallback, MessageCreated
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.errors import ApiError
from app.bot.chat import Reply, menu, respond
from app.core.config import Settings
from app.db.connector import Database
from app.db.models.route import Student
from app.route.service import act_on_notification


def create_route_router(database: Database | None, settings: Settings) -> maxapi.Router:
    router = maxapi.Router(router_id="olympiad_route")
    username = settings.bot.username if settings.bot else ""

    async def reply(user_id: int, text: str) -> Reply:
        if database is None:
            return Reply("Сервис временно недоступен. Попробуйте позже.")
        try:
            async with database.session_factory() as db:
                key = f"max:{user_id}"
                user = await db.get(Student, key)
                if user is None:
                    user = Student(id=key, max_user_id=user_id, profile={})
                    db.add(user)
                    try:
                        await db.commit()
                    except IntegrityError:
                        await db.rollback()
                        user = await db.get(Student, key)
                        if user is None:
                            raise
                return await respond(db, user, text, settings.demo_enabled)
        except ApiError as exc:
            return Reply(exc.message, menu())
        except ValidationError:
            return Reply("Проверьте настройки. Часовой пояс задаётся как Europe/Moscow.", menu())

    async def start(event: BotStarted) -> None:
        if event.bot is None:
            return
        result = await reply(event.user.user_id, "/start")
        await event.bot.send_message(
            user_id=event.user.user_id, text=result.text, attachments=result.attachments(username)
        )

    async def message(event: MessageCreated) -> None:
        sender = event.message.sender
        if sender is None or event.message.recipient.chat_type != "dialog":
            return
        text = event.message.body.text if event.message.body else ""
        result = await reply(sender.user_id, text or "/help")
        await event.message.answer(text=result.text, attachments=result.attachments(username))

    async def callback(event: MessageCallback) -> None:
        raw = event.callback.payload or ""
        if raw.startswith("chat:"):
            # Never expose a personal route in a group or forwarded conversation.
            if event.message is None or event.message.recipient.chat_type != "dialog":
                await event.answer(notification="Откройте личный чат с ботом")
                return
            if event.bot is None:
                return
            result = await reply(event.callback.user.user_id, "/" + raw[5:])
            await event.answer(notification="Готово")
            await event.bot.send_message(
                user_id=event.callback.user.user_id,
                text=result.text,
                attachments=result.attachments(username),
            )
            return
        payload = (event.callback.payload or "").split(":")
        if len(payload) != 3 or payload[0] != "route":
            return
        action, job_id = payload[1:]
        if action not in {"registered", "snooze", "remove", "read"}:
            return
        if database is None:
            await event.answer(notification="Сервис временно недоступен")
            return
        try:
            async with database.session_factory() as db:
                await act_on_notification(db, f"max:{event.callback.user.user_id}", job_id, action)
            messages = {
                "registered": "Регистрация отмечена в маршруте",
                "snooze": "Напомним через час с учётом тихих часов",
                "remove": "Олимпиада удалена из трека",
                "read": "Отмечено",
            }
            await event.answer(notification=messages[action])
        except ApiError as exc:
            await event.answer(notification=exc.message)

    router.bot_started.register(start)
    router.message_created.register(message)
    router.message_callback.register(callback)
    return router
