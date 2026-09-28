"""Small editorial snapshot. Unknown rules/dates are deliberately not inferred."""

from typing import Literal

from app.api.errors import ApiError
from app.route.schemas import Benefit, Event, Olympiad, Program, Source


RULES = Source(
    url="https://ba.hse.ru/olimp",
    title="ВШЭ · поступление по олимпиадам, 2026",
    note="Таблица соответствия предметов ВсОШ программам московского кампуса; дипломы 2026 года.",
)
HSE = Source(
    url="https://talent.hse.ru/olimp/mmo/",
    title="Высшая проба · сайт организатора",
    note="Общая регистрация 20 августа — 22 сентября 2026, 14:00 мск. Есть исключения по профилям.",
)
VSOSH = Source(
    url="https://vserosolimp.edsoo.ru/",
    title="ВсОШ · официальный портал",
    note="Сроки начальных этапов зависят от региона. Уточните расписание у школьного координатора.",
)
VP_PROFILES: list[tuple[Literal["math", "informatics"], str]] = [
    ("math", "Математика"),
    ("informatics", "Информатика"),
]
PROGRAMS = [
    Program(
        id="hse-pmi",
        name="Прикладная математика и информатика",
        short_name="ПМИ",
        description="Алгоритмы, математика, машинное обучение и исследование данных.",
    ),
    Program(
        id="hse-se",
        name="Программная инженерия",
        short_name="ПИ",
        description="Создание программных систем, разработка продуктов и инженерные практики.",
    ),
]


def vsosh_benefit(
    program_id: str, profile: str, kind: Literal["bvi", "100", "unknown"] = "bvi"
) -> Benefit:
    return Benefit(
        program_id=program_id,
        kind=kind,
        result="Победитель или призёр заключительного этапа ВсОШ",
        confirmation="Для этой льготы ВсОШ подтверждение результатом ЕГЭ не требуется.",
        explanation=f"В таблице приёма 2026 года указан профиль «{profile}». "
        "Участие и результаты школьного/муниципального этапов не дают эту льготу.",
        source=RULES,
    )


def unknown_benefit(program_id: str) -> Benefit:
    return Benefit(
        program_id=program_id,
        kind="unknown",
        result="Требуется проверка приложения к правилам",
        confirmation="Профиль, класс диплома и порог ЕГЭ для этой связи ещё не проверены.",
        explanation="Наличие олимпиады в каталоге не подтверждает БВИ на выбранную программу.",
        source=RULES,
    )


OLYMPIADS = [
    Olympiad(
        id="vsosh-math",
        name="Всероссийская олимпиада школьников",
        profile="Математика",
        subject="math",
        kind="vsosh",
        grades=[9, 10, 11],
        level="Школьный → заключительный этап",
        description="Последовательный маршрут из четырёх этапов. Начните с расписания вашей школы.",
        registration_url=VSOSH.url,
        source=VSOSH,
        benefits=[vsosh_benefit(p.id, "математика") for p in PROGRAMS],
        events=[
            Event(id="school", title="Школьный этап: уточните дату", kind="stage", source=VSOSH)
        ],
    ),
    Olympiad(
        id="vsosh-programming",
        name="Всероссийская олимпиада школьников",
        profile="Программирование",
        subject="informatics",
        kind="vsosh",
        grades=[9, 10, 11],
        level="Школьный → заключительный этап",
        description="Профиль информатики для тех, кому интересны алгоритмы и программирование.",
        registration_url=VSOSH.url,
        source=VSOSH,
        benefits=[vsosh_benefit(p.id, "программирование") for p in PROGRAMS],
        events=[
            Event(id="school", title="Школьный этап: уточните дату", kind="stage", source=VSOSH)
        ],
    ),
    Olympiad(
        id="vsosh-ai",
        name="Всероссийская олимпиада школьников",
        profile="Искусственный интеллект",
        subject="informatics",
        kind="vsosh",
        grades=[9, 10, 11],
        level="Школьный → заключительный этап",
        description=(
            "Профиль информатики. Условия льгот различаются даже между близкими программами."
        ),
        registration_url=VSOSH.url,
        source=VSOSH,
        benefits=[vsosh_benefit("hse-pmi", "искусственный интеллект"), unknown_benefit("hse-se")],
        events=[
            Event(id="school", title="Школьный этап: уточните дату", kind="stage", source=VSOSH)
        ],
    ),
    *[
        Olympiad(
            id=f"vp-{subject}",
            name="Высшая проба",
            profile=profile,
            subject=subject,
            kind="listed",
            grades=[9, 10, 11],
            description="Олимпиада НИУ ВШЭ. Проверьте требования к диплому для своей программы.",
            registration_url=HSE.url,
            source=HSE,
            benefits=[unknown_benefit(p.id) for p in PROGRAMS],
            events=[
                Event(
                    id="registration",
                    title="Регистрация",
                    kind="registration",
                    starts_at="2026-08-20T00:00:00+03:00",
                    deadline="2026-09-22T14:00:00+03:00",
                    source=HSE,
                ),
                Event(
                    id="qualifier",
                    title="Отборочный этап: проверьте расписание профиля",
                    kind="stage",
                    source=HSE,
                ),
            ],
        )
        for subject, profile in VP_PROFILES
    ],
]
BY_ID = {item.id: item for item in OLYMPIADS}


def get_olympiad(olympiad_id: str) -> Olympiad:
    if olympiad_id not in BY_ID:
        raise ApiError(404, "olympiad_not_found", "Олимпиада не найдена")
    return BY_ID[olympiad_id]
