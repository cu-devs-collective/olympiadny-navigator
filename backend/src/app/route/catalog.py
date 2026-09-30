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


SUBJECT_DESCRIPTIONS = {
    "math": "Алгебра, геометрия, комбинаторика и теория чисел. Задачи с доказательствами и "
    "развёрнутыми решениями.",
    "informatics": "Алгоритмические задачи: нужно разработать решение и написать программу, "
    "которая пройдёт тесты.",
    "physics": "Механика, электричество, оптика и термодинамика. В задачах важны физическая "
    "модель и обоснование решения.",
    "chemistry": "Расчёты, химические реакции и свойства веществ. Задачи объединяют несколько "
    "разделов химии.",
    "biology": "Ботаника, зоология, анатомия и генетика. Работа с биологическими данными, схемами "
    "и экспериментами.",
    "history": "Анализ исторических источников, карт и событий. Нужно сопоставлять факты и "
    "аргументировать выводы.",
    "social": "Право, экономика, социология и политология. Анализ текстов, общественных ситуаций "
    "и аргументов.",
    "russian": "Лингвистические задачи о звуках, словах и грамматике. Поиск закономерностей и "
    "объяснение языковых явлений.",
    "literature": "Анализ художественных текстов: композиции, образов и языка. Развёрнутые ответы "
    "с опорой на произведение.",
    "english": "Понимание английской речи и текстов, лексика, грамматика и письменная "
    "аргументация.",
    "geography": "Работа с картами и географическими данными. Природные процессы, население и "
    "хозяйство разных территорий.",
    "economics": "Микро- и макроэкономика, расчёты и анализ графиков. Объяснение поведения "
    "рынков, фирм и потребителей.",
}

OLYMPIADS = [
    Olympiad(
        id="vsosh-math",
        name="Всероссийская олимпиада школьников",
        profile="Математика",
        subject="math",
        kind="vsosh",
        grades=[9, 10, 11],
        level="Школьный → заключительный этап",
        description="Алгебра, геометрия, комбинаторика и теория чисел. Задачи с доказательствами "
        "и развёрнутыми решениями.",
        registration_url=VSOSH.url,
        source=VSOSH,
        benefits=[vsosh_benefit(p.id, "математика") for p in PROGRAMS],
        events=[Event(id="school", title="Школьный этап", kind="stage", source=VSOSH)],
    ),
    Olympiad(
        id="vsosh-programming",
        name="Всероссийская олимпиада школьников",
        profile="Программирование",
        subject="informatics",
        kind="vsosh",
        grades=[9, 10, 11],
        level="Школьный → заключительный этап",
        description="Алгоритмические задачи: нужно разработать решение и написать программу, "
        "которая пройдёт тесты.",
        registration_url=VSOSH.url,
        source=VSOSH,
        benefits=[vsosh_benefit(p.id, "программирование") for p in PROGRAMS],
        events=[Event(id="school", title="Школьный этап", kind="stage", source=VSOSH)],
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
            "Задачи по анализу данных и машинному обучению: подготовка данных, построение и "
            "оценка моделей."
        ),
        registration_url=VSOSH.url,
        source=VSOSH,
        benefits=[vsosh_benefit("hse-pmi", "искусственный интеллект"), unknown_benefit("hse-se")],
        events=[Event(id="school", title="Школьный этап", kind="stage", source=VSOSH)],
    ),
    *[
        Olympiad(
            id=f"vp-{subject}",
            name="Высшая проба",
            profile=profile,
            subject=subject,
            kind="listed",
            grades=[9, 10, 11],
            description=SUBJECT_DESCRIPTIONS[subject],
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
    note="Регистрация и подтверждение данных — не позднее 24 часов до тура. Время московское.",
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
                description=SUBJECT_DESCRIPTIONS[subject],
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
            description="Математические задачи с числовым ответом. На дистанционный тур отводится "
            "три часа.",
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
            description=SUBJECT_DESCRIPTIONS[subject.id],
            registration_url=VSOSH.url,
            source=VSOSH,
            benefits=[],
            events=[Event(id="school", title="Школьный этап", kind="stage", source=VSOSH)],
        )
    )

# Levels are tied to a published registry edition, not inferred for a future season.
REGISTRY = Source(
    url="https://rsr-olymp.ru/archive/2025",
    title="РСОШ · перечень 2025/26 · приказ № 669 от 30.08.2025",
    note="Уровень относится к профилю в перечне 2025/26, а не ко всем профилям олимпиады.",
)
VALIDITY = Source(
    url="https://ba.hse.ru/olimpinfo",
    title="ВШЭ · срок действия олимпиадного диплома",
    note="Четыре года после года проведения. БВИ зависит от правил программы в год поступления.",
)
for subject in SUBJECTS:
    if subject.id in {
        "physics",
        "chemistry",
        "biology",
        "history",
        "social",
        "russian",
        "literature",
        "english",
    }:
        OLYMPIADS.append(
            Olympiad(
                id=f"lomonosov-{subject.id}",
                name="Ломоносов",
                profile=subject.name,
                subject=subject.id,
                kind="listed",
                grades=[9, 10, 11],
                description=SUBJECT_DESCRIPTIONS[subject.id],
                source=LOMONOSOV,
                registration_url=LOMONOSOV.url,
                benefits=[],
                events=[
                    Event(
                        id="registration",
                        title="Регистрация · вторая половина октября",
                        kind="registration",
                        source=LOMONOSOV,
                    )
                ],
            )
        )
OLYMPIADS.extend(
    [
        Olympiad(
            id="fiztech-physics",
            name="Физтех",
            profile="Физика",
            subject="physics",
            kind="listed",
            grades=[9, 10, 11],
            source=MIPT,
            registration_url=MIPT.url,
            description="Письменные задачи по физике. Онлайн-тур длится четыре часа; в решении "
            "нужно обосновать расчёты.",
            benefits=[],
            events=[
                Event(
                    id="registration-1",
                    title="Регистрация на I тур",
                    kind="registration",
                    starts_at="2026-09-07T10:00:00+03:00",
                    deadline="2026-10-03T10:00:00+03:00",
                    source=MIPT,
                ),
                Event(
                    id="qualifier-1",
                    title="Начало I тура",
                    kind="stage",
                    starts_at="2026-10-04T10:00:00+03:00",
                    deadline="2026-10-04T10:00:00+03:00",
                    source=MIPT,
                ),
                Event(
                    id="registration-2",
                    title="Регистрация на II тур",
                    kind="registration",
                    deadline="2026-10-24T08:00:00+03:00",
                    source=MIPT,
                ),
                Event(
                    id="qualifier-2",
                    title="Начало II тура",
                    kind="stage",
                    starts_at="2026-10-25T08:00:00+03:00",
                    source=MIPT,
                ),
            ],
        ),
        Olympiad(
            id="rosatom-physics",
            name="Росатом",
            profile="Физика",
            subject="physics",
            kind="listed",
            grades=[9, 10, 11],
            source=ROSATOM,
            registration_url="https://org.mephi.ru/",
            description="Физические задачи с числовым ответом. Дистанционный тур длится три часа, "
            "на решение даётся одна попытка.",
            benefits=[],
            events=[
                Event(
                    id="online",
                    title="Интернет-тур · 17 ноября — 21 декабря",
                    kind="stage",
                    source=ROSATOM,
                )
            ],
        ),
        Olympiad(
            id="moscow-math",
            name="Московская олимпиада школьников",
            profile="Математика",
            subject="math",
            kind="listed",
            grades=[9, 10, 11],
            source=REGISTRY,
            registration_url="https://olympiads.mccme.ru/mmo/",
            description="Математические задачи с развёрнутыми доказательствами. Оцениваются "
            "решение и ход рассуждений.",
            benefits=[],
            events=[],
            aliases=["ММО", "МОШ"],
        ),
        Olympiad(
            id="spbu-informatics",
            name="Олимпиада школьников СПбГУ",
            profile="Информатика",
            subject="informatics",
            kind="listed",
            grades=[9, 10, 11],
            source=REGISTRY,
            registration_url="https://olympiada.spbu.ru/",
            description="Алгоритмы и программирование. Для каждой задачи нужно написать решение с "
            "учётом ограничений по времени и памяти.",
            benefits=[],
            events=[],
            aliases=["СПБГУ", "Санкт-Петербургский государственный университет"],
        ),
        Olympiad(
            id="technocup-informatics",
            name="ТехноКубок",
            profile="Программирование",
            subject="informatics",
            kind="listed",
            grades=[9, 10, 11],
            source=REGISTRY,
            registration_url="https://techno-cup.ru/",
            description="Соревнование по алгоритмическому программированию. Решения проверяются "
            "автоматически на наборе тестов.",
            benefits=[],
            events=[],
            aliases=["Технокубок", "информатика"],
        ),
    ]
)
LEVELS: dict[str, Literal[1, 2, 3]] = {
    "vp-math": 1,
    "vp-informatics": 1,
    "fiztech-math": 2,
    "fiztech-physics": 1,
    "lomonosov-math": 1,
    "lomonosov-informatics": 2,
    "rosatom-math": 2,
    "rosatom-physics": 1,
    "moscow-math": 1,
    "spbu-informatics": 1,
    "technocup-informatics": 2,
}
# Read from the two program-specific 2026 admission tables, including merged PDF cells.
PROGRAM_RULES = {
    "hse-pmi": Source(
        url="https://ba.hse.ru/mirror/pubs/share/1120646366",
        title="ВШЭ · ПМИ · особые права 2026, приложение 2",
    ),
    "hse-se": Source(
        url="https://ba.hse.ru/mirror/pubs/share/1120646612",
        title="ВШЭ · Программная инженерия · особые права 2026, приложение 2",
    ),
}
for olympiad in OLYMPIADS:
    if olympiad.id == "vsosh-physics":
        olympiad.benefits = [vsosh_benefit(p, "физика") for p in PROGRAM_RULES]
    if olympiad.id not in {
        "vp-math",
        "vp-informatics",
        "fiztech-math",
        "rosatom-math",
        "lomonosov-math",
        "lomonosov-informatics",
        "lomonosov-russian",
        "moscow-math",
        "spbu-informatics",
        "technocup-informatics",
    }:
        continue
    for program_id, rule_source in PROGRAM_RULES.items():
        bvi = olympiad.id.startswith("vp-") or (
            program_id == "hse-se"
            and olympiad.id
            in {
                "moscow-math",
                "spbu-informatics",
                "technocup-informatics",
            }
        )
        winner_only = bvi and (program_id == "hse-pmi" or olympiad.id == "spbu-informatics")
        threshold = (
            (85 if program_id == "hse-pmi" else 80)
            if olympiad.subject == "math"
            else (75 if olympiad.subject == "russian" else (90 if program_id == "hse-pmi" else 85))
        )
        subject_name = next(s.name for s in SUBJECTS if s.id == olympiad.subject)
        benefit = Benefit(
            program_id=program_id,
            kind="bvi" if bvi else "100",
            diploma_grades=[11],
            result="Победитель заключительного этапа"
            if winner_only
            else "Победитель или призёр заключительного этапа",
            confirmation=f"ЕГЭ: {subject_name.lower()} — от {threshold} баллов. "
            "Для отдельных категорий поступающих действует порог 65 (см. источник).",
            explanation=(
                "Призёрам доступно 100 баллов по предмету вместо БВИ. " if winner_only else ""
            )
            + "Учитывается диплом за 11 класс; правила приёма 2026 года.",
            source=rule_source,
        )
        olympiad.benefits = [b for b in olympiad.benefits if b.program_id != program_id]
        olympiad.benefits.append(benefit)

for olympiad in OLYMPIADS:
    if olympiad.id.startswith("lomonosov-"):
        LEVELS.setdefault(olympiad.id, 1)
    if olympiad.kind == "vsosh":
        olympiad.aliases.extend(["ВсОШ", "всеросс", "всероссийская", "всош " + olympiad.profile])
        if olympiad.subject == "informatics":
            olympiad.aliases.append("информатика")
    if olympiad.id in LEVELS:
        olympiad.registry_level = LEVELS[olympiad.id]
        olympiad.registry_season = "2025/26"
        olympiad.registry_source = REGISTRY
        olympiad.level = f"{olympiad.registry_level} уровень РСОШ · 2025/26"
    for benefit in olympiad.benefits:
        if benefit.kind != "unknown":
            benefit.diploma_validity_years = 4
            benefit.validity_source = VALIDITY

# Program pages establish entries, not BVI benefits.
PROGRAMS.extend(
    [
        Program(
            id="cu-mcs",
            name="Математика и компьютерные науки",
            short_name="МКН",
            university="Центральный университет",
            campus="Москва",
            direction="02.03.01 Математика и компьютерные науки",
            description="Математика, разработка программ и искусственный интеллект.",
            url="https://cu.ru/bachelor",
        ),
        Program(
            id="mephi-se",
            name="Математическое и программное обеспечение вычислительных машин "
            "и компьютерных сетей",
            short_name="Программная инженерия",
            university="НИЯУ МИФИ",
            campus="Москва",
            direction="09.03.04 Программная инженерия",
            description="Разработка программных систем, алгоритмы и компьютерные сети.",
            url="https://eis.mephi.ru/programs/Program/Details/385",
        ),
        Program(
            id="mipt-physics",
            name="Физика перспективных технологий",
            short_name="ФПТ",
            university="МФТИ (Физтех)",
            campus="Долгопрудный",
            direction="03.03.01 Прикладные математика и физика",
            description="Теоретическая и экспериментальная физика, работа на базовых кафедрах.",
            url="https://pkfefm.mipt.ru/",
        ),
        Program(
            id="bmstu-cad",
            name="Системы автоматизированного проектирования",
            short_name="САПР",
            university="МГТУ им. Н. Э. Баумана",
            campus="Москва",
            direction="09.03.01 Информатика и вычислительная техника",
            description="Программирование, компьютерная графика и инженерное проектирование.",
            url="https://rk6.bmstu.ru/enrollees/бакалавриат/",
        ),
        Program(
            id="msu-pmi",
            name="Прикладная математика и информатика",
            short_name="ПМИ · ВМК",
            university="МГУ им. М. В. Ломоносова",
            campus="Москва",
            direction="01.03.02 Прикладная математика и информатика",
            description="Математическое моделирование, численные методы и программирование.",
            url="https://pk.cs.msu.ru/bak_educational_programs",
        ),
    ]
)

BY_ID = {item.id: item for item in OLYMPIADS}


def get_olympiad(olympiad_id: str) -> Olympiad:
    if olympiad_id not in BY_ID:
        raise ApiError(404, "olympiad_not_found", "Олимпиада не найдена")
    return BY_ID[olympiad_id]
