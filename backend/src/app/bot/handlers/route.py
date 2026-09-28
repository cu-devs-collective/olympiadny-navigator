import maxapi
from maxapi.types import BotStarted, MessageCallback, MessageCreated
from sqlalchemy.exc import IntegrityError

from app.api.errors import ApiError
from app.bot.notifications import route_buttons
from app.core.config import Settings
from app.db.connector import Database
from app.db.models.route import Student
from app.route.service import act_on_notification, stop_notifications


WELCOME = (
    "Олимпиадный маршрут 🧭\n\n"
    "Выберите программы вуза, соберите свой трек и следите за олимпиадами. "
    "В мини-приложении — условия льгот и источники; здесь — ваши напоминания.\n\n"
    "Откройте маршрут и включите сообщения в профиле. "
    "Команда /stop отключает напоминания. /start возвращает к маршруту."
)


def create_route_router(database: Database | None, settings: Settings) -> maxapi.Router:
    router = maxapi.Router(router_id="olympiad_route")
    username = settings.bot.username if settings.bot else ""

    async def start(event: BotStarted) -> None:
        if event.bot is None:
            return
        if database:
            async with database.session_factory() as db:
                user_id = f"max:{event.user.user_id}"
                if not await db.get(Student, user_id):
                    db.add(Student(id=user_id, max_user_id=event.user.user_id, profile={}))
                    try:
                        await db.commit()
                    except IntegrityError:
                        await db.rollback()
        await event.bot.send_message(
            user_id=event.user.user_id, text=WELCOME, attachments=route_buttons(username)
        )

    async def message(event: MessageCreated) -> None:
        sender = event.message.sender
        # Personal profiles are only managed from direct conversations.
        if sender is None or event.message.recipient.chat_type != "dialog":
            return
        text = event.message.body.text if event.message.body else ""
        if text == "/stop" and database:
            async with database.session_factory() as db:
                user = await db.get(Student, f"max:{sender.user_id}")
                if user:
                    await stop_notifications(db, user.id)
            await event.message.answer(text="Напоминания отключены. Включить их можно в профиле.")
        else:
            await event.message.answer(text=WELCOME, attachments=route_buttons(username))

    async def callback(event: MessageCallback) -> None:
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
