"""Editorial snapshot of real olympiads. Unknown rules and dates are not inferred."""

from typing import Literal

from app.api.errors import ApiError
from app.route.schemas import Benefit, Event, Olympiad, Program, Source, Subject


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
        direction="09.03.04 Программная инженерия",
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
# Dates below are a manually checked snapshot, not a live organizer feed.
MIPT = Source(
    url="https://olymp-online.mipt.ru/",
    title="Физтех · расписание 2026/27",
    note="Для первого тура нужны регистрация и подтверждение данных до 10 октября, 10:00 мск.",
)
LOMONOSOV = Source(
    url="https://olymp.msu.ru/",
    title="Ломоносов · официальный сайт МГУ",
    note="Анонс 23.09.2026: регистрация во второй половине октября. Точный график ожидается.",
)
ROSATOM = Source(
    url="https://olymp.mephi.ru/rosatom/stages/qualification",
    title="Росатом · отборочный этап",
    note="Интернет-тур 17 ноября — 21 декабря 2026. Точное время окончания не опубликовано.",
)
OLYMPIADS.extend(
    [
        Olympiad(
            id="fiztech-math",
            name="Физтех",
            profile="Математика",
            subject="math",
            kind="listed",
            grades=[9, 10, 11],
            source=MIPT,
            registration_url=MIPT.url,
            description="Олимпиада МФТИ. Онлайн-отбор с письменными решениями и очный финал.",
            benefits=[unknown_benefit(p.id) for p in PROGRAMS],
            events=[
                Event(
                    id="registration-1",
                    title="Регистрация и подтверждение данных · I тур",
                    kind="registration",
                    starts_at="2026-09-07T10:00:00+03:00",
                    deadline="2026-10-10T10:00:00+03:00",
                    source=MIPT,
                ),
                Event(
                    id="qualifier-1",
                    title="Начало I тура",
                    kind="stage",
                    starts_at="2026-10-11T10:00:00+03:00",
                    deadline="2026-10-11T10:00:00+03:00",
                    source=MIPT,
                ),
                Event(
                    id="qualifier-2",
                    title="Начало II тура (если не прошли I тур)",
                    kind="stage",
                    starts_at="2026-11-01T08:00:00+03:00",
                    source=MIPT,
                ),
            ],
        ),
        *[
            Olympiad(
                id=f"lomonosov-{subject}",
                name="Ломоносов",
                profile=profile,
                subject=subject,
                kind="listed",
                grades=[9, 10, 11],
                source=LOMONOSOV,
                registration_url=LOMONOSOV.url,
                description="Олимпиада МГУ: дистанционный отбор и заключительный этап по профилю.",
                benefits=[unknown_benefit(p.id) for p in PROGRAMS],
                events=[
                    Event(
                        id="registration",
                        title="Регистрация · вторая половина октября",
                        kind="registration",
                        source=LOMONOSOV,
                    )
                ],
            )
            for subject, profile in VP_PROFILES
        ],
        Olympiad(
            id="rosatom-math",
            name="Росатом",
            profile="Математика",
            subject="math",
            kind="listed",
            grades=[9, 10, 11],
            source=ROSATOM,
            registration_url="https://org.mephi.ru/",
            description="Олимпиада НИЯУ МИФИ. Можно выбрать дистанционный отборочный тур.",
            benefits=[unknown_benefit(p.id) for p in PROGRAMS],
            events=[
                Event(
                    id="online",
                    title="Интернет-тур · 17 ноября — 21 декабря",
                    kind="stage",
                    source=ROSATOM,
                )
            ],
        ),
    ]
)
PROGRAMS.extend(
    [
        Program(
            id="itmo-ct",
            name="Компьютерные технологии",
            short_name="КТ",
            university="Университет ИТМО",
            campus="Санкт-Петербург",
            description="Направление 01.03.02: прикладная математика и информатика.",
            url="https://abit.itmo.ru/programs/bachelor",
        ),
        Program(
            id="itmo-software",
            direction="09.03.04 Программная инженерия",
            name="Системное и прикладное программное обеспечение",
            short_name="СППО",
            university="Университет ИТМО",
            campus="Санкт-Петербург",
            description="Направление 09.03.04: программная инженерия.",
            url="https://abit.itmo.ru/program/bachelor/system_software",
        ),
    ]
)
# A real program is not evidence of any particular olympiad admission benefit.
for olympiad in OLYMPIADS:
    for program in PROGRAMS[2:]:
        olympiad.benefits.append(
            Benefit(
                program_id=program.id,
                kind="unknown",
                result="Условия связи не проверены",
                confirmation="Нужно проверить профиль диплома, класс и подтверждение ЕГЭ.",
                explanation="Программа есть в каталоге ИТМО. БВИ по олимпиаде не подтверждено.",
                source=Source(
                    url=program.url,
                    title=f"ИТМО · {program.short_name}",
                    note="Источник подтверждает программу, а не олимпиадную льготу.",
                ),
            )
        )

SUBJECTS = [
    Subject(id="math", name="Математика"),
    Subject(id="informatics", name="Информатика"),
    Subject(id="physics", name="Физика"),
    Subject(id="chemistry", name="Химия"),
    Subject(id="biology", name="Биология"),
    Subject(id="history", name="История"),
    Subject(id="social", name="Обществознание"),
    Subject(id="russian", name="Русский язык"),
    Subject(id="literature", name="Литература"),
    Subject(id="english", name="Английский язык"),
    Subject(id="geography", name="География"),
    Subject(id="economics", name="Экономика"),
]
for subject in SUBJECTS[2:]:
    OLYMPIADS.append(
        Olympiad(
            id=f"vsosh-{subject.id}",
            name="Всероссийская олимпиада школьников",
            profile=subject.name,
            subject=subject.id,
            kind="vsosh",
            grades=[9, 10, 11],
            level="Школьный → заключительный этап",
            description=f"ВсОШ · {subject.name}. Дату школьного этапа уточните в своей школе.",
            registration_url=VSOSH.url,
            source=VSOSH,
            benefits=[],
            events=[Event(id="school", title="Школьный этап", kind="stage", source=VSOSH)],
        )
    )

BY_ID = {item.id: item for item in OLYMPIADS}


def get_olympiad(olympiad_id: str) -> Olympiad:
    if olympiad_id not in BY_ID:
        raise ApiError(404, "olympiad_not_found", "Олимпиада не найдена")
    return BY_ID[olympiad_id]
