import asyncio
import typing
from types import SimpleNamespace
from unittest import mock

import pytest
from maxapi.enums import UpdateType

from app.bot.dispatcher import create_dispatcher
from app.bot.handlers.repeater import repeat_message
from app.bot.runner import configure_webhook, run_bot, run_long_polling, run_webhook
from app.core.config import BotSettings, Settings


def test_dispatcher_builds_fresh_feature_router_tree() -> None:
    first_dispatcher = create_dispatcher()
    second_dispatcher = create_dispatcher()

    handlers_router = first_dispatcher.routers[0]
    repeater_router = handlers_router.routers[0]

    assert handlers_router.router_id == "handlers"
    assert repeater_router.router_id == "repeater"
    assert len(repeater_router.event_handlers) == 1
    assert first_dispatcher.routers[0] is not second_dispatcher.routers[0]
    assert first_dispatcher.routers[0].routers[0] is not second_dispatcher.routers[0].routers[0]


def test_repeat_message_copies_text_and_attachments() -> None:
    attachments = [object()]
    message = SimpleNamespace(
        body=SimpleNamespace(text="hello", attachments=attachments),
        answer=mock.AsyncMock(),
    )

    event = typing.cast(typing.Any, SimpleNamespace(message=message))
    asyncio.run(repeat_message(event))

    message.answer.assert_awaited_once_with(text="hello", attachments=attachments)


def test_repeat_message_ignores_message_without_body() -> None:
    message = SimpleNamespace(body=None, answer=mock.AsyncMock())

    event = typing.cast(typing.Any, SimpleNamespace(message=message))
    asyncio.run(repeat_message(event))

    message.answer.assert_not_awaited()


def test_run_bot_requires_token() -> None:
    with pytest.raises(RuntimeError, match="APP_BOT_TOKEN"):
        asyncio.run(run_bot(Settings(bot=None)))


def test_configure_webhook_refreshes_existing_subscription() -> None:
    bot = mock.MagicMock()
    bot.get_subscriptions = mock.AsyncMock(
        return_value=SimpleNamespace(
            subscriptions=[SimpleNamespace(url="https://example.com/webhook")]
        )
    )
    bot.unsubscribe_webhook = mock.AsyncMock()
    bot.subscribe_webhook = mock.AsyncMock(return_value=SimpleNamespace(success=True))
    settings = BotSettings.model_validate(
        {
            "token": "token",
            "mode": "webhook",
            "webhook_url": "https://example.com/webhook",
            "webhook_secret": "secret-value",
        }
    )

    asyncio.run(configure_webhook(bot, settings))

    bot.unsubscribe_webhook.assert_awaited_once_with("https://example.com/webhook")
    bot.subscribe_webhook.assert_awaited_once_with(
        url="https://example.com/webhook",
        update_types=[UpdateType.MESSAGE_CREATED],
        secret="secret-value",
    )


def test_long_polling_transport_starts_and_stops_dispatcher() -> None:
    bot = mock.MagicMock()
    bot.delete_webhook = mock.AsyncMock()
    dispatcher = mock.MagicMock()
    dispatcher.start_polling = mock.AsyncMock()
    dispatcher.stop_polling = mock.AsyncMock()

    asyncio.run(run_long_polling(bot, dispatcher))

    bot.delete_webhook.assert_awaited_once_with()
    dispatcher.start_polling.assert_awaited_once_with(bot, skip_updates=True)
    dispatcher.stop_polling.assert_awaited_once_with()


def test_webhook_transport_starts_secured_server() -> None:
    bot = mock.MagicMock()
    bot.get_subscriptions = mock.AsyncMock(return_value=SimpleNamespace(subscriptions=[]))
    bot.subscribe_webhook = mock.AsyncMock(return_value=SimpleNamespace(success=True))
    dispatcher = mock.MagicMock()
    dispatcher.handle_webhook = mock.AsyncMock()
    settings = BotSettings.model_validate(
        {
            "token": "token",
            "mode": "webhook",
            "webhook_url": "https://example.com/webhook",
            "webhook_secret": "secret-value",
        }
    )

    asyncio.run(run_webhook(bot, dispatcher, settings))

    dispatcher.handle_webhook.assert_awaited_once_with(
        bot,
        host="0.0.0.0",
        port=8080,
        path="/webhook",
        secret="secret-value",
    )
