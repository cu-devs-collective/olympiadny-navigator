import loguru
import maxapi
from maxapi.enums import UpdateType

from app.bot.dispatcher import create_dispatcher
from app.core.config import BotMode, BotSettings, Settings, get_settings


def create_bot(settings: BotSettings) -> maxapi.Bot:
    return maxapi.Bot(token=settings.token.get_secret_value())


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
        update_types=[UpdateType.MESSAGE_CREATED],
        secret=settings.webhook_secret.get_secret_value(),
    )
    if not result.success:
        message = result.message or "unknown MAX API error"
        raise RuntimeError(f"Failed to configure MAX webhook: {message}")


async def run_long_polling(bot: maxapi.Bot, dispatcher: maxapi.Dispatcher) -> None:
    await bot.delete_webhook()
    loguru.logger.info("MAX message repeater started in long-polling mode")
    try:
        await dispatcher.start_polling(bot, skip_updates=True)
    finally:
        await dispatcher.stop_polling()
        loguru.logger.info("MAX message repeater long polling stopped")


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
        "MAX message repeater webhook started at {0}",
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
        loguru.logger.info("MAX message repeater webhook stopped")


async def run_bot(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    bot_settings = settings.bot
    if bot_settings is None:
        raise RuntimeError("APP_BOT_TOKEN is required to start the MAX bot")

    bot = create_bot(bot_settings)
    dispatcher = create_dispatcher()

    try:
        if bot_settings.mode is BotMode.WEBHOOK:
            await run_webhook(bot, dispatcher, bot_settings)
        else:
            await run_long_polling(bot, dispatcher)
    finally:
        await bot.close_session()
