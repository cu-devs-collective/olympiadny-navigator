from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

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
from maxapi.types.attachments.buttons import InlineButtonUnion
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.route import Student
from app.route.catalog import OLYMPIADS, PROGRAMS, get_olympiad
from app.route.schemas import Profile
from app.route.service import (
    add_track,
    change_track,
    create_demo_event,
    list_track,
    lock_student,
    save_profile,
    stop_notifications,
    sync_reminders,
)


Button = InlineButtonUnion
STATES = {"planned": "В плане", "registered": "Регистрация отмечена", "completed": "Завершено"}
HELP = (
    "Олимпиадный навигатор\n\n"
    "Здесь можно собрать маршрут целиком, проверить сроки и отметить регистрацию.\n\n"
    "/profile: класс и цели\n"
    "/catalog: олимпиады; можно написать «Физтех» или «математика»\n"
    "/track: мой маршрут и действия\n"
    "/deadlines: ближайшие сроки\n"
    "/settings: сообщения и тихие часы\n"
    "/stop: отключить напоминания\n\n"
    "Напоминания приходят сюда. Мини-приложение удобно для сравнения условий и календаря."
)


def button(label: str, command: str) -> CallbackButton:
    return CallbackButton(text=label, payload=f"chat:{command}")


@dataclass
class Reply:
    text: str
    rows: list[list[Button]] = field(default_factory=list)

    def attachments(
        self, username: str
    ) -> list[Attachment | InputMedia | InputMediaBuffer | AttachmentUpload]:
        rows = list(self.rows)
        if username:
            rows.append(
                [
                    LinkButton(
                        text="Открыть мини-приложение",
                        url=f"https://max.ru/{username}?startapp=route",
                    )
                ]
            )
        return (
            [Attachment(type=AttachmentType.INLINE_KEYBOARD, payload=ButtonsPayload(buttons=rows))]
            if rows
            else []
        )


def menu() -> list[list[Button]]:
    return [
        [button("Мой навигатор", "track"), button("Ближайшие сроки", "deadlines")],
        [button("Найти олимпиаду", "catalog"), button("Мой профиль", "profile")],
        [button("Настройки сообщений", "settings")],
    ]


def title(olympiad) -> str:
    name = "ВсОШ" if olympiad.kind == "vsosh" else olympiad.name
    return f"{name} · {olympiad.profile}"


def profile_reply(profile: Profile) -> Reply:
    goals = [f"{p.university} · {p.short_name}" for p in PROGRAMS if p.id in profile.program_ids]
    rows: list[list[Button]] = [
        [
            button(f"{'✓ ' if profile.grade == g else ''}{g} класс", f"grade {g}")
            for g in (9, 10, 11)
        ]
    ]
    rows.extend(
        [
            [
                button(
                    f"{'✓ ' if p.id in profile.program_ids else ''}{p.university} · {p.short_name}",
                    f"goal {p.id}",
                )
            ]
            for p in PROGRAMS
        ]
    )
    rows.append([button("Сохранить профиль", "save")])
    return Reply(
        f"Ваш профиль\n{profile.grade} класс → поступление в {profile.admission_year}\n"
        f"Цели: {', '.join(goals) or 'не выбраны'}\n\n"
        "Выберите класс и интересующие программы. Год рассчитывается по окончанию 11 класса.\n\n"
        + "\n".join(f"{p.university} · {p.short_name}: {p.name}" for p in PROGRAMS),
        rows,
    )


def consent_reply() -> Reply:
    return Reply(
        "Олимпиадный навигатор\n\n"
        "Для работы сохраняем MAX ID, класс, цели, настройки и отметки. "
        "Профиль и данные можно удалить в приложении.\n"
        "Нажмите «Принимаю», чтобы продолжить.",
        [[button("Принимаю", "accept")]],
    )


async def respond(db: AsyncSession, user: Student, raw: str, demo_enabled: bool) -> Reply:
    text = raw.strip()
    command, _, argument = text.lstrip("/").partition(" ")
    command = command.lower().split("@")[0]
    command = {
        "маршрут": "track",
        "сроки": "deadlines",
        "профиль": "profile",
        "настройки": "settings",
        "помощь": "help",
    }.get(command, command)
    argument = argument.strip()
    profile = Profile(**user.profile)
    if command == "start":
        user = await lock_student(db, user.id)
        user.profile = {**user.profile, "consent": False}
        await db.commit()
        return consent_reply()
    if command == "accept":
        user = await lock_student(db, user.id)
        user.profile = {**user.profile, "consent": True}
        await db.commit()
        return Reply(HELP, menu())
    if not profile.consent and command != "stop":
        return consent_reply()
    if command in {"help", "menu", "меню"}:
        return Reply(HELP, menu())
    if command in {"profile", "setup"}:
        return profile_reply(profile)
    if command in {"grade", "goal"}:
        user = await lock_student(db, user.id)
        profile = Profile(**user.profile)
        if command == "grade":
            if argument not in {"9", "10", "11"}:
                return Reply("Выберите класс: /grade 9, /grade 10 или /grade 11.")
            profile = Profile(**{**profile.model_dump(), "grade": int(argument)})
        else:
            if argument not in {p.id for p in PROGRAMS}:
                return profile_reply(profile)
            goals = list(profile.program_ids)
            if argument in goals:
                goals.remove(argument)
            else:
                goals.append(argument)
            profile.program_ids = goals
        user.profile = profile.model_dump()
        await sync_reminders(db, user)
        await db.commit()
        return profile_reply(profile)
    if command == "save":
        user = await lock_student(db, user.id)
        profile = Profile(**user.profile)
        await save_profile(db, user.id, profile)
        return Reply(
            f"Профиль сохранён. Поступление в {profile.admission_year}.\n"
            "Теперь добавьте олимпиады и включите сообщения, если хотите получать сроки в чате.",
            [[button("Выбрать олимпиады", "catalog"), button("Включить сообщения", "resume")]],
        )
    if command == "settings":
        return Reply(
            f"Сообщения {'включены' if profile.notifications_enabled else 'отключены'}.\n"
            f"Тихие часы: {profile.quiet_start:02}:00-{profile.quiet_end:02}:00 "
            f"({profile.timezone}).\n\n"
            "Изменить часы: /quiet 22 8. Без тихих часов: /quiet 0 0.\n"
            "Часовой пояс: /timezone Asia/Yekaterinburg.\n"
            "Напоминаем за 7 дней и за сутки до проверенного срока. "
            "Для событий без точной даты напоминания пока недоступны.",
            [
                [
                    button(
                        "Отключить" if profile.notifications_enabled else "Включить сообщения",
                        "stop" if profile.notifications_enabled else "resume",
                    )
                ],
                [button("Тихие часы 22-08", "quiet 22 8"), button("Без тихих часов", "quiet 0 0")],
            ],
        )
    if command == "stop":
        await stop_notifications(db, user.id)
        return Reply("Напоминания отключены. /resume: снова включить.", menu())
    if command in {"resume", "quiet", "timezone"}:
        user = await lock_student(db, user.id)
        values = Profile(**user.profile).model_dump()
        if not values["consent"] or not values["program_ids"]:
            return Reply(
                "Сначала выберите цели и сохраните профиль с согласием.",
                [[button("Настроить профиль", "profile")]],
            )
        if command == "resume":
            values["notifications_enabled"] = True
        elif command == "quiet":
            hours = argument.split()
            if len(hours) != 2 or any(not h.isdigit() or not 0 <= int(h) <= 23 for h in hours):
                return Reply("Укажите часы от 0 до 23, например: /quiet 22 8.")
            values["quiet_start"], values["quiet_end"] = map(int, hours)
        else:
            values["timezone"] = argument
        await save_profile(db, user.id, Profile(**values))
        return await respond(db, user, "settings", demo_enabled)
    if command in {"catalog", "catalog-page"} or (
        not text.startswith("/")
        and command
        not in {
            "track",
            "track-page",
            "deadlines",
            "show",
            "add",
            "registered",
            "done",
            "remove",
            "confirm-remove",
            "demo",
        }
    ):
        page = 0
        if command == "catalog-page":
            number, _, query = argument.partition(" ")
            page = int(number) if number.isdigit() else 0
        else:
            query = argument if command == "catalog" else text
        query = query.casefold().replace("ё", "е")
        matches = [
            o
            for o in OLYMPIADS
            if query in f"{o.name} {o.profile} {' '.join(o.aliases)}".casefold().replace("ё", "е")
        ]
        if not matches:
            return Reply("Не нашёл такую олимпиаду. Попробуйте «математика» или «Физтех».", menu())
        page = min(page, (len(matches) - 1) // 12)
        rows = [[button(title(o), f"show {o.id}")] for o in matches[page * 12 : (page + 1) * 12]]
        navigation = []
        if page:
            navigation.append(button("Назад", f"catalog-page {page - 1} {query}"))
        if (page + 1) * 12 < len(matches):
            navigation.append(button("Далее", f"catalog-page {page + 1} {query}"))
        if navigation:
            rows.append(navigation)
        return Reply(
            f"Олимпиады: {len(matches)} · страница {page + 1}/{(len(matches) + 11) // 12}. "
            "Выберите, чтобы посмотреть сроки и условия льгот.",
            rows,
        )
    if command in {"track", "track-page"}:
        route = await list_track(db, user.id)
        if not route.items:
            return Reply(
                "Маршрут пока пуст. Настройте профиль и выберите первую олимпиаду.", menu()
            )
        lines = ["Ваш навигатор"]
        rows: list[list[Button]] = []
        page = int(argument) if command == "track-page" and argument.isdigit() else 0
        page = min(page, (len(route.items) - 1) // 12)
        for entry in route.items[page * 12 : (page + 1) * 12]:
            o = get_olympiad(entry.olympiad_id)
            lines.append(f"• {o.name} · {o.profile}: {STATES[entry.status]}")
            rows.append([button(title(o), f"show {o.id}")])
        navigation = []
        if page:
            navigation.append(button("Назад", f"track-page {page - 1}"))
        if (page + 1) * 12 < len(route.items):
            navigation.append(button("Далее", f"track-page {page + 1}"))
        if navigation:
            rows.append(navigation)
        return Reply("\n".join(lines), rows)
    if command == "deadlines":
        route = await list_track(db, user.id)
        now = datetime.now().timestamp()
        events = sorted(
            [
                (datetime.fromisoformat(e.deadline).timestamp(), o, e)
                for t in route.items
                if t.status != "completed"
                for o in [get_olympiad(t.olympiad_id)]
                for e in o.events
                if e.deadline
                and datetime.fromisoformat(e.deadline).timestamp() > now
                and (e.kind != "registration" or t.status == "planned")
            ],
            key=lambda x: x[0],
        )
        lines = ["Ближайшие сроки вашего маршрута"]
        for stamp, o, e in events[:10]:
            day = datetime.fromtimestamp(stamp, ZoneInfo(profile.timezone)).strftime(
                "%d.%m.%Y %H:%M"
            )
            lines.append(f"\n{day} · {o.name}, {o.profile}\n{e.title}\n{e.source.url}")
        if not events:
            lines.append(
                "\nПроверенных будущих сроков пока нет. "
                "Даты без точного времени смотрите в карточках олимпиад."
            )
        lines.append(f"\nЧасовой пояс: {profile.timezone}. Сверяйте изменения с организатором.")
        return Reply("\n".join(lines), [[button("Мой навигатор", "track")]])
    if command in {"show", "add", "registered", "done", "remove", "confirm-remove", "demo"}:
        o = get_olympiad(argument)
        if command == "add":
            await add_track(db, user.id, o.id)
        elif command in {"registered", "done", "confirm-remove"}:
            state = {"registered": "registered", "done": "completed", "confirm-remove": None}[
                command
            ]
            await change_track(db, user.id, o.id, state)
            if command == "confirm-remove":
                return Reply("Удалено из маршрута. Будущие напоминания отменены.", menu())
        elif command == "remove":
            return Reply(
                f"Удалить {o.name} · {o.profile} из маршрута?",
                [
                    [
                        button("Да, удалить", f"confirm-remove {o.id}"),
                        button("Оставить", f"show {o.id}"),
                    ]
                ],
            )
        elif command == "demo":
            if not demo_enabled:
                return Reply("Демонстрационные события отключены.")
            await create_demo_event(db, user.id, o.id, "rule_change")
            return Reply(
                "Тестовое сообщение поставлено в очередь. Придёт с учётом тихих часов. "
                "Это пример, а не реальное изменение правил.",
                menu(),
            )
        route = await list_track(db, user.id)
        entry = next((i for i in route.items if i.olympiad_id == o.id), None)
        lines = [
            f"{o.name} · {o.profile}",
            o.description,
            (
                f"РСОШ · {o.registry_level} уровень · {o.registry_season}"
                if o.registry_level
                else "ВсОШ · уровни I-III РСОШ не применяются"
            ),
            f"\n{STATES[entry.status] if entry else 'Не добавлена в маршрут'}",
            "\nСроки (Москва):",
        ]
        for e in o.events:
            stamp = e.deadline or e.starts_at
            day = (
                datetime.fromisoformat(stamp).strftime("%d.%m.%Y %H:%M")
                if stamp
                else "дата уточняется"
            )
            lines.append(f"• {e.title}: {day}" if stamp else f"• {e.title}. {e.source.note}")
        lines.append(
            "\nПравила приёма указаны за 2026 год. "
            f"Для поступления в {profile.admission_year} проверь правила выбранного вуза."
        )
        for b in o.benefits:
            if profile.program_ids and b.program_id not in profile.program_ids:
                continue
            p = next(p for p in PROGRAMS if p.id == b.program_id)
            label = {"bvi": "БВИ", "100": "100 баллов", "unknown": "не проверено"}[b.kind]
            lines.append(
                f"\n{p.university} · {p.short_name}: {label}\n{b.result}\n"
                f"{b.confirmation}\n{b.source.url}"
            )
            if b.diploma_validity_years:
                lines.append(
                    f"Срок действия диплома: {b.diploma_validity_years} года после года олимпиады. "
                    "БВИ зависит от правил программы в год поступления."
                )
        if o.registry_source:
            lines.append(f"\nПеречень РСОШ: {o.registry_source.url}")
        lines.append(f"\nИсточник расписания: {o.source.url}\n{o.source.note}")
        rows = [[LinkButton(text="Сайт организатора", url=o.registration_url)]]
        if entry:
            rows.append(
                [
                    button("Я зарегистрировался", f"registered {o.id}"),
                    button("Завершил участие", f"done {o.id}"),
                ]
            )
            rows.append([button("Убрать из маршрута", f"remove {o.id}")])
            if demo_enabled:
                rows.append([button("Тест сообщения в чат", f"demo {o.id}")])
        else:
            rows.append([button("Добавить в маршрут", f"add {o.id}")])
        return Reply("\n".join(lines), rows)
    return Reply("Не знаю эту команду. /help: что умеет бот.", menu())
