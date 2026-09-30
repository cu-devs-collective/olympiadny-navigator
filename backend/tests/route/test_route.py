import asyncio
import hashlib
import hmac
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.app import create_app
from app.api.errors import ApiError
from app.bot.notifications import dispatch_due
from app.core.config import BotSettings, DatabaseSettings, Settings
from app.db.base import Base
from app.db.connector import Database
from app.db.models.route import Reminder
from app.route.auth import validate_init_data
from app.route.catalog import BY_ID
from app.route.schemas import Event, Profile
from app.route.service import quiet_until


TOKEN = "test-bot-token"


def signed_data(user_id: int | str = 123, age=0, **extra):
    data = {"user": json.dumps({"id": user_id}), "auth_date": str(int(time.time()) - age), **extra}
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


@pytest.fixture
def settings(tmp_path: Path):
    return Settings(
        database=DatabaseSettings(url=f"sqlite+aiosqlite:///{tmp_path}/test.db"),
        demo_enabled=True,
        bot=BotSettings(token=SecretStr(TOKEN)),
    )


@pytest.fixture
def client(settings):
    async def prepare():
        db = Database(settings.database)
        async with db.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await db.close()

    asyncio.run(prepare())
    with TestClient(create_app(settings)) as client:
        yield client


def login(client, max_id=None):
    response = (
        client.post("/api/v1/auth/max", json={"init_data": signed_data(max_id)})
        if max_id
        else client.post("/api/v1/auth/demo")
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def setup_profile(client, headers, notifications=True):
    profile = Profile(
        program_ids=["hse-pmi", "hse-se"],
        consent=True,
        notifications_enabled=notifications,
        quiet_start=0,
        quiet_end=0,
    ).model_dump()
    response = client.put("/api/v1/me", headers=headers, json=profile)
    assert response.status_code == 200, response.text
    return profile


def test_complete_personal_route_and_delete(client):
    headers = login(client)
    setup_profile(client, headers)
    for _ in range(2):
        response = client.put("/api/v1/track/vsosh-math", headers=headers)
        assert response.status_code == 200
        assert len(response.json()["items"]) == 1
    event = client.post(
        "/api/v1/demo/events", headers=headers, json={"olympiad_id": "vsosh-math"}
    ).json()
    assert event["state"] == "preview"
    assert event["is_demo"] is True
    response = client.post(
        f"/api/v1/notifications/{event['id']}/actions",
        headers=headers,
        json={"action": "registered"},
    )
    assert response.status_code == 200, response.text
    assert client.get("/api/v1/track", headers=headers).json()["items"][0]["status"] == "registered"
    assert client.delete("/api/v1/me", headers=headers).status_code == 200
    assert client.get("/api/v1/me", headers=headers).status_code == 401


def test_profiles_are_isolated_and_callbacks_cannot_target_another_student(client):
    first, second = login(client), login(client)
    setup_profile(client, first)
    setup_profile(client, second)
    client.put("/api/v1/track/vsosh-math", headers=first)
    event = client.post(
        "/api/v1/demo/events", headers=first, json={"olympiad_id": "vsosh-math"}
    ).json()
    assert client.get("/api/v1/track", headers=second).json()["items"] == []
    assert client.get("/api/v1/notifications", headers=second).json()["items"] == []
    assert (
        client.post(
            f"/api/v1/notifications/{event['id']}/actions",
            headers=second,
            json={"action": "registered"},
        ).status_code
        == 404
    )
    assert client.delete("/api/v1/track/vsosh-math", headers=second).status_code == 404


def test_max_sessions_reuse_profile_and_survive_api_restart(client, settings):
    first = login(client, 456)
    setup_profile(client, first)
    client.put("/api/v1/track/vsosh-programming", headers=first)
    with TestClient(create_app(settings)) as restarted:
        second = login(restarted, 456)
        assert restarted.get("/api/v1/me", headers=first).json()["is_demo"] is False
        assert (
            restarted.get("/api/v1/track", headers=second).json()["items"][0]["olympiad_id"]
            == "vsosh-programming"
        )


@pytest.mark.parametrize(
    "data",
    [
        "user=bad",
        signed_data(age=7200),
        signed_data(age=-120),
        signed_data(user_id="123"),
        signed_data() + "&user=123",
        signed_data().replace("123", "124"),
    ],
)
def test_invalid_max_identity_is_rejected(data):
    with pytest.raises(ApiError):
        validate_init_data(data, TOKEN, 3600)


def test_valid_max_signature_with_urlencoded_characters():
    assert validate_init_data(signed_data(start_param="тест + & ="), TOKEN, 3600) == 123


def test_unknown_rules_and_expired_deadlines_are_not_invented(client):
    catalog = client.get("/api/v1/catalog").json()
    higher = next(o for o in catalog["olympiads"] if o["id"] == "vp-math")
    assert all(
        b["kind"] == "unknown" for b in higher["benefits"] if b["program_id"].startswith("itmo-")
    )
    assert higher["events"][0]["deadline"] == "2026-09-22T14:00:00+03:00"
    assert higher["events"][1]["deadline"] is None
    assert all(b["admission_year"] == 2026 for o in catalog["olympiads"] for b in o["benefits"])


def test_private_routes_require_session_and_profile_validation(client):
    assert client.get("/api/v1/me").status_code == 401
    assert client.get("/api/v1/track").status_code == 401
    headers = login(client)
    assert client.put("/api/v1/track/vsosh-math", headers=headers).status_code == 409
    profile = setup_profile(client, headers)
    for field, value in [
        ("program_ids", ["unknown"]),
        ("program_ids", []),
        ("timezone", "Mars/Crater"),
        ("subjects", []),
        ("consent", False),
    ]:
        assert (
            client.put("/api/v1/me", headers=headers, json={**profile, field: value}).status_code
            == 422
        )
    assert client.put("/api/v1/track/no-such-olympiad", headers=headers).status_code == 404
    assert (
        client.patch(
            "/api/v1/track/vsosh-math", headers=headers, json={"status": "winner"}
        ).status_code
        == 422
    )


def test_demo_disabled_by_default(settings):
    settings.demo_enabled = False
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/catalog").json()["demo_enabled"] is False
        assert client.post("/api/v1/auth/demo").status_code == 403


def test_opt_out_cancels_pending_notifications(client):
    headers = login(client, 123)
    profile = setup_profile(client, headers)
    client.put("/api/v1/track/vsosh-math", headers=headers)
    response = client.post(
        "/api/v1/demo/events", headers=headers, json={"olympiad_id": "vsosh-math"}
    )
    assert response.status_code == 200
    assert response.json()["state"] == "pending"
    client.put("/api/v1/me", headers=headers, json={**profile, "notifications_enabled": False})
    assert (
        client.get("/api/v1/notifications", headers=headers).json()["items"][0]["state"]
        == "cancelled"
    )
    assert (
        client.post(
            "/api/v1/demo/events", headers=headers, json={"olympiad_id": "vsosh-math"}
        ).status_code
        == 409
    )


def test_removed_track_makes_old_notification_safe(client):
    headers = login(client)
    setup_profile(client, headers)
    client.put("/api/v1/track/vsosh-math", headers=headers)
    job = client.post(
        "/api/v1/demo/events", headers=headers, json={"olympiad_id": "vsosh-math"}
    ).json()
    client.delete("/api/v1/track/vsosh-math", headers=headers)
    assert (
        client.post(
            f"/api/v1/notifications/{job['id']}/actions",
            headers=headers,
            json={"action": "registered"},
        ).status_code
        == 409
    )


def test_snooze_idempotency_and_rule_change_is_only_a_demo(client):
    headers = login(client)
    setup_profile(client, headers)
    client.put("/api/v1/track/vsosh-math", headers=headers)
    before = client.get("/api/v1/catalog").json()
    job = client.post(
        "/api/v1/demo/events",
        headers=headers,
        json={"olympiad_id": "vsosh-math", "kind": "rule_change"},
    ).json()
    assert job["is_demo"] is True
    assert client.get("/api/v1/catalog").json() == before
    path = f"/api/v1/notifications/{job['id']}/actions"
    assert client.post(path, headers=headers, json={"action": "registered"}).status_code == 422
    assert client.post(path, headers=headers, json={"action": "snooze"}).status_code == 200
    assert client.post(path, headers=headers, json={"action": "snooze"}).status_code == 409
    assert (
        client.post(
            "/api/v1/demo/events", headers=headers, json={"olympiad_id": "vsosh-math"}
        ).status_code
        == 429
    )


def test_quiet_hours_handle_overnight_and_same_day_intervals():
    from datetime import datetime

    now = datetime.fromisoformat("2026-09-30T23:30:00+03:00").timestamp()
    assert (
        quiet_until(Profile(), now)
        == datetime.fromisoformat("2026-10-01T08:00:00+03:00").timestamp()
    )
    assert quiet_until(Profile(quiet_start=0, quiet_end=0), now) is None
    midday = datetime.fromisoformat("2026-09-30T12:00:00+03:00").timestamp()
    assert quiet_until(Profile(), midday) is None
    assert quiet_until(Profile(quiet_start=10, quiet_end=14), midday) == midday + 7200


def test_worker_sends_once_and_respects_opt_out(client, settings):
    headers = login(client, 123)
    setup_profile(client, headers)
    client.put("/api/v1/track/vsosh-math", headers=headers)
    job = client.post(
        "/api/v1/demo/events", headers=headers, json={"olympiad_id": "vsosh-math"}
    ).json()

    async def run():
        db = Database(settings.database)
        bot = AsyncMock()
        with patch("app.bot.notifications.asyncio.sleep", new=AsyncMock()):
            assert await dispatch_due(db, bot, "route_bot") == 1
            assert await dispatch_due(db, bot, "route_bot") == 0
        assert bot.send_message.await_count == 1
        kwargs = bot.send_message.call_args.kwargs
        assert kwargs["user_id"] == 123
        assert (
            kwargs["attachments"][0].payload.buttons[1][0].payload
            == f"route:registered:{job['id']}"
        )
        await db.close()

    asyncio.run(run())
    assert (
        client.get("/api/v1/notifications", headers=headers).json()["items"][0]["state"] == "sent"
    )


def test_ambiguous_delivery_failure_is_not_retried(client, settings):
    headers = login(client, 123)
    setup_profile(client, headers)
    client.put("/api/v1/track/vsosh-math", headers=headers)
    client.post("/api/v1/demo/events", headers=headers, json={"olympiad_id": "vsosh-math"})

    async def run():
        db = Database(settings.database)
        bot = AsyncMock()
        bot.send_message.side_effect = TimeoutError("ambiguous transport failure")
        with patch("app.bot.notifications.asyncio.sleep", new=AsyncMock()):
            assert await dispatch_due(db, bot, "") == 0
            assert await dispatch_due(db, bot, "") == 0
        assert bot.send_message.await_count == 1
        await db.close()

    asyncio.run(run())
    assert (
        client.get("/api/v1/notifications", headers=headers).json()["items"][0]["state"] == "failed"
    )


def test_planning_skips_past_reminders_and_keeps_stage_after_registration(client, settings):
    from datetime import UTC, datetime

    headers = login(client, 123)
    setup_profile(client, headers)
    olympiad = BY_ID["vsosh-math"]
    original = olympiad.events
    now = time.time()
    future = datetime.fromtimestamp(now + 10 * 86400, UTC).isoformat()
    past = datetime.fromtimestamp(now - 86400, UTC).isoformat()
    olympiad.events = [
        Event(
            id="registration",
            title="Registration",
            kind="registration",
            deadline=future,
            source=olympiad.source,
        ),
        Event(id="stage", title="Stage", kind="stage", deadline=future, source=olympiad.source),
        Event(id="past", title="Past", kind="registration", deadline=past, source=olympiad.source),
    ]
    try:
        client.put("/api/v1/track/vsosh-math", headers=headers)
        client.put("/api/v1/track/vsosh-math", headers=headers)
        jobs = client.get("/api/v1/notifications", headers=headers).json()["items"]
        assert len(jobs) == 2
        assert all(j["kind"] == "registration" for j in jobs)
        client.patch("/api/v1/track/vsosh-math", headers=headers, json={"status": "registered"})
        jobs = client.get("/api/v1/notifications", headers=headers).json()["items"]
        assert len(jobs) == 4
        assert all(j["state"] == "cancelled" for j in jobs if j["kind"] == "registration")
        assert all(j["state"] == "pending" for j in jobs if j["kind"] == "stage")
    finally:
        olympiad.events = original


def test_worker_quiet_hours_and_expiry(client, settings):
    from datetime import datetime

    headers = login(client, 123)
    profile = setup_profile(client, headers)
    client.put("/api/v1/me", headers=headers, json={**profile, "quiet_start": 22, "quiet_end": 8})
    client.put("/api/v1/track/vsosh-math", headers=headers)
    now = datetime.fromisoformat("2026-09-30T23:30:00+03:00").timestamp()

    async def run():
        db = Database(settings.database)
        async with db.session_factory() as s:
            s.add(
                Reminder(
                    id="quiet",
                    user_id="max:123",
                    olympiad_id="vsosh-math",
                    dedup_key="quiet",
                    kind="registration",
                    due_at=now - 5,
                    deadline=now + 86400,
                    content={"title": "test", "text": "test"},
                )
            )
            s.add(
                Reminder(
                    id="expired",
                    user_id="max:123",
                    olympiad_id="vsosh-math",
                    dedup_key="expired",
                    kind="registration",
                    due_at=now - 5,
                    deadline=now - 1,
                    content={"title": "test", "text": "test"},
                )
            )
            await s.commit()
        bot = AsyncMock()
        assert await dispatch_due(db, bot, "", now=now) == 0
        bot.send_message.assert_not_awaited()
        async with db.session_factory() as s:
            job = await s.get(Reminder, "quiet")
            assert job is not None
            assert job.state == "pending"
            assert job.due_at > now
            expired = await s.get(Reminder, "expired")
            assert expired is not None and expired.state == "cancelled"
        await db.close()

    asyncio.run(run())


def test_max_handlers_share_state_with_api_and_stop_reminders(client, settings):
    from types import SimpleNamespace

    from maxapi.enums import UpdateType

    from app.bot.handlers.route import create_route_router

    headers = login(client, 123)
    setup_profile(client, headers)
    client.put("/api/v1/track/vsosh-math", headers=headers)
    job = client.post(
        "/api/v1/demo/events", headers=headers, json={"olympiad_id": "vsosh-math"}
    ).json()

    async def run():
        database = Database(settings.database)
        handlers = {
            handler.update_type: handler.func_event
            for handler in create_route_router(database, settings).event_handlers
        }
        callback = SimpleNamespace(
            callback=SimpleNamespace(
                payload=f"route:registered:{job['id']}", user=SimpleNamespace(user_id=123)
            ),
            answer=AsyncMock(),
        )
        await handlers[UpdateType.MESSAGE_CALLBACK](callback)
        callback.answer.assert_awaited_once_with(notification="Регистрация отмечена в маршруте")
        message = SimpleNamespace(
            sender=SimpleNamespace(user_id=123),
            recipient=SimpleNamespace(chat_type="dialog"),
            body=SimpleNamespace(text="/stop"),
            answer=AsyncMock(),
        )
        await handlers[UpdateType.MESSAGE_CREATED](SimpleNamespace(message=message))
        message.answer.assert_awaited_once()
        await database.close()

    asyncio.run(run())
    assert client.get("/api/v1/track", headers=headers).json()["items"][0]["status"] == "registered"
    assert (
        client.get("/api/v1/me", headers=headers).json()["profile"]["notifications_enabled"]
        is False
    )


def test_graduation_year_is_derived_and_cannot_be_overridden(client):
    from datetime import datetime

    from app.route.schemas import admission_year_for_grade

    assert admission_year_for_grade(11, datetime(2026, 9, 1)) == 2027
    assert admission_year_for_grade(10, datetime(2027, 2, 1)) == 2028
    assert admission_year_for_grade(9, datetime(2026, 8, 31)) == 2028
    headers = login(client)
    profile = setup_profile(client, headers)
    profile.update(grade=9, admission_year=2035)
    saved = client.put("/api/v1/me", headers=headers, json=profile)
    assert saved.status_code == 200
    assert saved.json()["profile"]["admission_year"] == admission_year_for_grade(9)


def test_chat_onboarding_and_actions_without_miniapp(client, settings):
    from types import SimpleNamespace

    from maxapi.enums import UpdateType

    from app.bot.handlers.route import create_route_router

    async def run():
        database = Database(settings.database)
        handlers = {
            h.update_type: h.func_event
            for h in create_route_router(database, settings).event_handlers
        }

        async def send(text, user_id=777):
            answer = AsyncMock()
            event = SimpleNamespace(
                message=SimpleNamespace(
                    sender=SimpleNamespace(user_id=user_id),
                    recipient=SimpleNamespace(chat_type="dialog"),
                    body=SimpleNamespace(text=text),
                    answer=answer,
                )
            )
            await handlers[UpdateType.MESSAGE_CREATED](event)
            return answer.call_args.kwargs["text"]

        assert "навигатор" in await send("/start")
        assert "Принимаю" in await send("/resume")
        await send("/accept")
        assert "9 класс" in await send("/grade 9")
        await send("/goal hse-pmi")
        assert "сохранён" in await send("/save")
        assert "включены" in await send("/resume")
        assert "Физтех" in await send("/add fiztech-math")
        assert "Физтех" in await send("/track")
        assert "100 баллов" in await send("/show fiztech-math")
        assert "Регистрация отмечена" in await send("/registered fiztech-math")
        await send("/accept", user_id=778)
        assert "пуст" in await send("/track", user_id=778)
        assert "Удалить" in await send("/remove fiztech-math")
        assert "Физтех" in await send("/track")  # confirmation required
        assert "Удалено" in await send("/confirm-remove fiztech-math")
        assert "пуст" in await send("/track")
        assert "отключены" in await send("/stop")
        await database.close()

    asyncio.run(run())
    headers = login(client, 777)
    profile = client.get("/api/v1/me", headers=headers).json()["profile"]
    assert profile["grade"] == 9
    assert profile["program_ids"] == ["hse-pmi"]
    assert profile["consent"] is True
    assert profile["notifications_enabled"] is False


def test_chat_buttons_apply_to_clicker_only_and_ignore_groups(client, settings):
    from types import SimpleNamespace

    from maxapi.enums import UpdateType

    from app.bot.handlers.route import create_route_router

    owner = login(client, 111)
    other = login(client, 222)
    setup_profile(client, owner)
    setup_profile(client, other)
    client.put("/api/v1/track/vsosh-math", headers=owner)

    async def run():
        database = Database(settings.database)
        handlers = {
            h.update_type: h.func_event
            for h in create_route_router(database, settings).event_handlers
        }
        bot = SimpleNamespace(send_message=AsyncMock())
        event = SimpleNamespace(
            callback=SimpleNamespace(
                payload="chat:registered vsosh-math", user=SimpleNamespace(user_id=222)
            ),
            message=SimpleNamespace(recipient=SimpleNamespace(chat_type="dialog")),
            answer=AsyncMock(),
            bot=bot,
        )
        await handlers[UpdateType.MESSAGE_CALLBACK](event)
        assert "удалена" in bot.send_message.call_args.kwargs["text"]
        bot.send_message.reset_mock()
        event.message.recipient.chat_type = "chat"
        await handlers[UpdateType.MESSAGE_CALLBACK](event)
        bot.send_message.assert_not_awaited()
        await database.close()

    asyncio.run(run())
    assert client.get("/api/v1/track", headers=owner).json()["items"][0]["status"] == "planned"


def test_chat_stop_resume_restores_only_unsent_future_reminders(client, settings):
    from datetime import UTC, datetime

    from app.bot.chat import respond
    from app.db.models.route import Student

    headers = login(client, 123)
    setup_profile(client, headers)
    olympiad = BY_ID["vsosh-math"]
    event = Event(
        id="future",
        title="Registration",
        kind="registration",
        deadline=datetime.fromtimestamp(time.time() + 12 * 86400, UTC).isoformat(),
        source=olympiad.source,
    )
    with patch.object(olympiad, "events", [event]):
        client.put("/api/v1/track/vsosh-math", headers=headers)

        async def run():
            database = Database(settings.database)
            async with database.session_factory() as db:
                user = await db.get(Student, "max:123")
                assert user is not None
                await respond(db, user, "/stop", True)
                await respond(db, user, "/resume", True)
            await database.close()

        asyncio.run(run())
        jobs = client.get("/api/v1/notifications", headers=headers).json()["items"]
        assert len(jobs) == 2
        assert all(j["state"] == "pending" for j in jobs)


def test_miniapp_profile_edit_preserves_chat_notification_settings(client):
    headers = login(client, 123)
    profile = setup_profile(client, headers)
    for key in ("notifications_enabled", "quiet_start", "quiet_end"):
        del profile[key]
    profile["grade"] = 11
    response = client.put("/api/v1/me", headers=headers, json=profile)
    assert response.status_code == 200
    saved = response.json()["profile"]
    assert saved["notifications_enabled"] is True
    assert saved["quiet_start"] == 0
    assert saved["quiet_end"] == 0


def test_consent_is_independent_of_programs_and_start_resets_it(client, settings):
    from app.bot.chat import respond
    from app.db.models.route import Student

    headers = login(client, 987)
    assert (
        client.post("/api/v1/me/consent", headers=headers, json={"accepted": False}).status_code
        == 422
    )
    result = client.post("/api/v1/me/consent", headers=headers, json={"accepted": True})
    assert result.status_code == 200
    assert result.json()["profile"]["consent"] is True
    assert result.json()["profile"]["program_ids"] == []

    async def restart():
        database = Database(settings.database)
        async with database.session_factory() as db:
            user = await db.get(Student, "max:987")
            assert user is not None
            reply = await respond(db, user, "/start", True)
            assert "Принимаю" in reply.text
        await database.close()

    asyncio.run(restart())
    assert client.get("/api/v1/me", headers=headers).json()["profile"]["consent"] is False


def test_extended_subjects_are_saved_and_supported_by_catalog(client):
    headers = login(client)
    profile = setup_profile(client, headers)
    catalog = client.get("/api/v1/catalog").json()
    profile["subjects"] = [s["id"] for s in catalog["subjects"]]
    assert len(profile["subjects"]) == 12
    response = client.put("/api/v1/me", headers=headers, json=profile)
    assert response.status_code == 200
    assert set(response.json()["profile"]["subjects"]) == {
        o["subject"] for o in catalog["olympiads"]
    }
    assert client.put("/api/v1/track/vsosh-chemistry", headers=headers).status_code == 200


def test_many_programs_and_catalog_provenance(client):
    headers = login(client)
    profile = setup_profile(client, headers)
    catalog = client.get("/api/v1/catalog").json()
    profile["program_ids"] = [p["id"] for p in catalog["programs"]]
    saved = client.put("/api/v1/me", headers=headers, json=profile)
    assert saved.status_code == 200
    assert len(saved.json()["profile"]["program_ids"]) == len(catalog["programs"]) == 9
    olympiads = {o["id"]: o for o in catalog["olympiads"]}
    assert len(olympiads) == 32
    assert olympiads["fiztech-math"]["registry_level"] == 2
    assert olympiads["fiztech-physics"]["registry_level"] == 1
    assert olympiads["fiztech-physics"]["registry_season"] == "2025/26"
    assert olympiads["vsosh-math"]["registry_level"] is None
    assert "ВсОШ" in olympiads["vsosh-math"]["aliases"]
    vp = {b["program_id"]: b for b in olympiads["vp-math"]["benefits"]}
    assert vp["hse-pmi"]["kind"] == "bvi"
    assert vp["hse-pmi"]["diploma_grades"] == [11]
    assert vp["hse-pmi"]["diploma_validity_years"] == 4
    assert "85" in vp["hse-pmi"]["confirmation"]
    assert "80" in vp["hse-se"]["confirmation"]
    assert vp["itmo-ct"]["diploma_validity_years"] is None


def test_chat_deeplink_keeps_consent_and_catalog_paginates(client, settings):
    from types import SimpleNamespace

    from maxapi.enums import UpdateType

    from app.bot.chat import respond
    from app.bot.handlers.route import create_route_router
    from app.db.models.route import Student

    headers = login(client, 888)
    setup_profile(client, headers)
    client.put("/api/v1/track/vsosh-math", headers=headers)

    async def run():
        database = Database(settings.database)
        handlers = {
            h.update_type: h.func_event
            for h in create_route_router(database, settings).event_handlers
        }
        bot = SimpleNamespace(send_message=AsyncMock())
        await handlers[UpdateType.BOT_STARTED](
            SimpleNamespace(
                bot=bot,
                user=SimpleNamespace(user_id=888),
                payload="navigator",
            )
        )
        assert "Математика" in bot.send_message.call_args.kwargs["text"]
        async with database.session_factory() as db:
            user = await db.get(Student, "max:888")
            assert user is not None
            assert user.profile["consent"] is True
            for p in ["itmo-ct", "itmo-software"]:
                await respond(db, user, f"/goal {p}", True)
            assert len(user.profile["program_ids"]) == 4
            result = await respond(db, user, "всош", True)
            assert "13" in result.text
            assert len(result.rows) == 13  # 12 results plus navigation
            assert "ВсОШ" in result.rows[0][0].text
            result = await respond(db, user, "/catalog-page 1 всош", True)
            assert len(result.rows) == 2
            result = await respond(db, user, "/catalog", True)
            assert len(result.rows) == 13
        await database.close()

    asyncio.run(run())
