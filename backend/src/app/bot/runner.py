import asyncio
import contextlib

import loguru
import maxapi
from maxapi.client.default import DefaultConnectionProperties
from maxapi.enums import UpdateType
from maxapi.types import BotCommand

from app.bot.dispatcher import create_dispatcher
from app.bot.notifications import notification_loop
from app.core.config import BotMode, BotSettings, Settings, get_settings
from app.db.connector import Database


def create_bot(settings: BotSettings) -> maxapi.Bot:
    # Retrying a POST after an ambiguous transport failure can duplicate a reminder.
    return maxapi.Bot(
        token=settings.token.get_secret_value(),
        default_connection=DefaultConnectionProperties(max_retries=0),
    )


async def configure_webhook(bot: maxapi.Bot, settings: BotSettings) -> None:
    if settings.webhook_url is None or settings.webhook_secret is None:
        raise RuntimeError(
            "APP_BOT_WEBHOOK_URL and APP_BOT_WEBHOOK_SECRET are required when APP_BOT_MODE=webhook"
        )

    webhook_url = str(settings.webhook_url)
    subscriptions = await bot.get_subscriptions()

    if any(subscription.url == webhook_url for subscription in subscriptions.subscriptions):
        await bot.unsubscribe_webhook(webhook_url)

    result = await bot.subscribe_webhook(
        url=webhook_url,
        update_types=[
            UpdateType.MESSAGE_CREATED,
            UpdateType.BOT_STARTED,
            UpdateType.MESSAGE_CALLBACK,
        ],
        secret=settings.webhook_secret.get_secret_value(),
    )
    if not result.success:
        message = result.message or "unknown MAX API error"
        raise RuntimeError(f"Failed to configure MAX webhook: {message}")


async def run_long_polling(bot: maxapi.Bot, dispatcher: maxapi.Dispatcher) -> None:
    await bot.delete_webhook()
    loguru.logger.info("Olympiad route bot started in long-polling mode")
    try:
        await dispatcher.start_polling(bot, skip_updates=False)
    finally:
        await dispatcher.stop_polling()
        loguru.logger.info("Olympiad route bot long polling stopped")


async def run_webhook(
    bot: maxapi.Bot,
    dispatcher: maxapi.Dispatcher,
    settings: BotSettings,
) -> None:
    if settings.webhook_url is None or settings.webhook_secret is None:
        raise RuntimeError(
            "APP_BOT_WEBHOOK_URL and APP_BOT_WEBHOOK_SECRET are required when APP_BOT_MODE=webhook"
        )

    await configure_webhook(bot, settings)
    loguru.logger.info(
        "Olympiad route bot webhook started at {0}",
        settings.webhook_url,
    )
    try:
        await dispatcher.handle_webhook(
            bot,
            host=settings.webhook_host,
            port=settings.webhook_port,
            path=settings.webhook_path,
            secret=settings.webhook_secret.get_secret_value(),
        )
    finally:
        loguru.logger.info("Olympiad route bot webhook stopped")


async def run_bot(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    bot_settings = settings.bot
    if bot_settings is None:
        raise RuntimeError("APP_BOT_TOKEN is required to start the MAX bot")

    if settings.database is None:
        raise RuntimeError("APP_DATABASE_URL is required to start the MAX bot")
    bot = create_bot(bot_settings)
    database = Database(settings.database)
    worker = None
    try:
        if not bot_settings.username:
            info = await bot.get_me()
            bot_settings.username = info.username or ""
        try:
            await bot.set_commands(
                *[
                    BotCommand(name=name, description=description)
                    for name, description in [
                        ("start", "Меню маршрута"),
                        ("profile", "Класс и программы вузов"),
                        ("catalog", "Найти олимпиаду"),
                        ("track", "Мой маршрут и отметки"),
                        ("deadlines", "Ближайшие сроки"),
                        ("settings", "Сообщения и тихие часы"),
                        ("stop", "Отключить напоминания"),
                        ("help", "Помощь"),
                    ]
                ]
            )
            loguru.logger.info("Chat command menu registered")
        except Exception:
            # Commands still work as text if MAX cannot update its menu right now.
            loguru.logger.warning("Could not register chat command menu")
        dispatcher = create_dispatcher(database, settings)
        worker = asyncio.create_task(notification_loop(database, bot, settings))
        if bot_settings.mode is BotMode.WEBHOOK:
            await run_webhook(bot, dispatcher, bot_settings)
        else:
            await run_long_polling(bot, dispatcher)
    finally:
        if worker is not None:
            worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker
        await database.close()
        await bot.close_session()
