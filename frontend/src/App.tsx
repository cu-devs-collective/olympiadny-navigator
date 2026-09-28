import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api, ApiError, openSource, session } from "./route-api";
import type {
  Catalog,
  Me,
  Notification,
  Olympiad,
  Profile,
  TrackEntry,
} from "./route-api";
import { Icon } from "./icons";
import "./App.css";

type Tab = "discover" | "track" | "calendar" | "notifications" | "profile";
const tabs: { id: Tab; label: string; icon: string }[] = [
  { id: "discover", label: "Обзор олимпиад", icon: "grid" },
  { id: "track", label: "Мой маршрут", icon: "route" },
  { id: "calendar", label: "Календарь", icon: "calendar" },
  { id: "notifications", label: "Напоминания", icon: "bell" },
  { id: "profile", label: "Мой профиль", icon: "user" },
];
const subjects = { math: "Математика", informatics: "Информатика" };
const statuses = {
  planned: "В плане",
  registered: "Регистрация отмечена",
  completed: "Участие завершено",
};
const delivery: Record<string, string> = {
  pending: "В очереди",
  sending: "Отправляется",
  sent: "Отправлено в MAX",
  preview: "Пример в браузере",
  failed: "Отправка не подтверждена",
  cancelled: "Отменено",
  read: "Прочитано",
};
const date = (value: string | number, timezone = "Europe/Moscow") =>
  new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  }).format(new Date(typeof value === "number" ? value * 1000 : value));

function registration(o: Olympiad, now: number) {
  const event = o.events.find((e) => e.kind === "registration");
  if (!event?.deadline) return { label: "Сроки уточняются", closed: false };
  if (new Date(event.deadline).getTime() < now)
    return { label: "Регистрация закрыта", closed: true };
  if (event.starts_at && new Date(event.starts_at).getTime() > now)
    return { label: "Регистрация впереди", closed: false };
  return { label: "Регистрация открыта", closed: false };
}

function Dialog({
  title,
  close,
  children,
  error,
}: {
  title: string;
  close: () => void;
  children: React.ReactNode;
  error?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    const dialog = ref.current;
    return () => dialog?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className="dialog"
      onCancel={close}
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div className="dialog-head">
        <h2>{title}</h2>
        <button className="icon-button" onClick={close} aria-label="Закрыть">
          <Icon name="close" />
        </button>
      </div>
      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}
      {children}
    </dialog>
  );
}

function ProfileForm({
  initial,
  catalog,
  save,
  busy,
  isDemo,
}: {
  initial: Profile;
  catalog: Catalog;
  save: (p: Profile) => void;
  busy: boolean;
  isDemo: boolean;
}) {
  const [p, setP] = useState(initial);
  function submit(e: FormEvent) {
    e.preventDefault();
    save(p);
  }
  function toggleProgram(id: string) {
    setP({
      ...p,
      program_ids: p.program_ids.includes(id)
        ? p.program_ids.filter((v) => v !== id)
        : [...p.program_ids, id],
    });
  }
  return (
    <form className="profile-form" onSubmit={submit}>
      <div>
        <span className="eyebrow">01 / ТОЧКА НАЗНАЧЕНИЯ</span>
        <h3>Куда хочешь поступить?</h3>
        <p className="muted">
          Выбери одну или две программы. Сравним их олимпиадные возможности.
        </p>
      </div>
      <div className="program-options">
        {catalog.programs.map((program) => (
          <label
            className={`program-option ${p.program_ids.includes(program.id) ? "selected" : ""}`}
            key={program.id}
          >
            <input
              type="checkbox"
              checked={p.program_ids.includes(program.id)}
              onChange={() => toggleProgram(program.id)}
            />
            <span>
              <small>
                {program.university} · {program.campus}
              </small>
              <strong>{program.name}</strong>
              <span className="muted">{program.description}</span>
            </span>
          </label>
        ))}
      </div>
      <div className="form-grid">
        <label>
          Сейчас учусь в
          <select
            value={p.grade}
            onChange={(e) =>
              setP({
                ...p,
                grade: +e.target.value,
                admission_year: new Date().getFullYear() + 12 - +e.target.value,
              })
            }
          >
            {[9, 10, 11].map((g) => (
              <option key={g} value={g}>
                {g} классе
              </option>
            ))}
          </select>
        </label>
        <label>
          Год поступления
          <select
            value={p.admission_year}
            onChange={(e) => setP({ ...p, admission_year: +e.target.value })}
          >
            {Array.from({ length: 10 }, (_, i) => 2026 + i).map((y) => (
              <option key={y}>{y}</option>
            ))}
          </select>
        </label>
      </div>
      <fieldset>
        <legend>Интересующие предметы</legend>
        <div className="subject-options">
          {(["math", "informatics"] as const).map((s) => (
            <label key={s}>
              <input
                type="checkbox"
                checked={p.subjects.includes(s)}
                onChange={() =>
                  setP({
                    ...p,
                    subjects: p.subjects.includes(s)
                      ? p.subjects.filter((v) => v !== s)
                      : [...p.subjects, s],
                  })
                }
              />
              {subjects[s]}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="form-divider" />
      <div>
        <span className="eyebrow">02 / НА СВЯЗИ</span>
        <h3>Напомним, когда пора действовать</h3>
      </div>
      <label className="toggle-row">
        <span>
          <strong>Напоминания {isDemo ? "в демо" : "в MAX"}</strong>
          <small>
            {isDemo
              ? "В браузере показываем пример сообщения. Реальная доставка доступна после входа из MAX."
              : "Регистрации, этапы и проверенные изменения. Можно отключить в любой момент."}
          </small>
        </span>
        <input
          type="checkbox"
          role="switch"
          checked={p.notifications_enabled}
          onChange={(e) =>
            setP({ ...p, notifications_enabled: e.target.checked })
          }
        />
      </label>
      <label>
        Часовой пояс
        <select
          value={p.timezone}
          onChange={(e) => setP({ ...p, timezone: e.target.value })}
        >
          {[
            "Europe/Kaliningrad",
            "Europe/Moscow",
            "Europe/Samara",
            "Asia/Yekaterinburg",
            "Asia/Omsk",
            "Asia/Krasnoyarsk",
            "Asia/Irkutsk",
            "Asia/Yakutsk",
            "Asia/Vladivostok",
            "Asia/Magadan",
            "Asia/Kamchatka",
          ].map((z) => (
            <option key={z} value={z}>
              {z.split("/")[1].replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </label>
      <div className="form-grid">
        <label>
          Не беспокоить с
          <select
            value={p.quiet_start}
            onChange={(e) => setP({ ...p, quiet_start: +e.target.value })}
          >
            {Array.from({ length: 24 }, (_, i) => (
              <option key={i} value={i}>
                {String(i).padStart(2, "0")}:00
              </option>
            ))}
          </select>
        </label>
        <label>
          До
          <select
            value={p.quiet_end}
            onChange={(e) => setP({ ...p, quiet_end: +e.target.value })}
          >
            {Array.from({ length: 24 }, (_, i) => (
              <option key={i} value={i}>
                {String(i).padStart(2, "0")}:00
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="small muted">
        Одинаковое время начала и окончания отключает тихие часы.
      </p>
      <label className="consent">
        <input
          type="checkbox"
          required
          checked={p.consent}
          onChange={(e) => setP({ ...p, consent: e.target.checked })}
        />
        <span>
          Разрешаю сохранять класс, цели, настройки и отметки для работы
          маршрута. При входе через MAX также сохраняется его идентификатор.
          Профиль можно удалить вместе с историей.
        </span>
      </label>
      <button
        className="button primary wide"
        disabled={
          busy || !p.program_ids.length || !p.subjects.length || !p.consent
        }
      >
        {busy ? "Сохраняем…" : "Сохранить мой маршрут"}
        <Icon name="arrow" />
      </button>
    </form>
  );
}

function App() {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 60000);
    return () => clearInterval(timer);
  }, []);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [track, setTrack] = useState<TrackEntry[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [tab, setTab] = useState<Tab>("discover");
  const [query, setQuery] = useState("");
  const [subject, setSubject] = useState("all");
  const [onlyRelevant, setOnlyRelevant] = useState(false);
  const [detail, setDetail] = useState<Olympiad | null>(null);
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  const refresh = useCallback(async () => {
    const [user, route, messages] = await Promise.all([
      api.me(),
      api.track(),
      api.notifications(),
    ]);
    setMe(user);
    setTrack(route.items);
    setNotifications(messages.items);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.catalog();
      setCatalog(data);
      const initData = window.WebApp?.initData;
      window.WebApp?.ready?.();
      if (initData) {
        const result = await api.login(initData);
        session.set(result.token);
      }
      if (session.get()) await refresh();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) session.clear();
      setError(e instanceof Error ? e.message : "Не удалось открыть маршрут");
    } finally {
      setLoading(false);
    }
  }, [refresh]);

  useEffect(() => {
    const timer = setTimeout(() => {
      void load();
    }, 0);
    return () => clearTimeout(timer);
  }, [load]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 4000);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    if (!me) return;
    const sync = () => {
      if (!document.hidden)
        void refresh().catch(() => {
          /* Keep the last known state until an explicit request. */
        });
    };
    const timer = setInterval(sync, 15000);
    window.addEventListener("focus", sync);
    return () => {
      clearInterval(timer);
      window.removeEventListener("focus", sync);
    };
  }, [me?.id, refresh]); // eslint-disable-line react-hooks/exhaustive-deps

  async function run(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        session.clear();
        setMe(null);
        setTrack([]);
        setNotifications([]);
      }
      setError(
        e instanceof Error ? e.message : "Не удалось выполнить действие",
      );
    } finally {
      setBusy(false);
    }
  }
  async function login() {
    if (!window.WebApp?.initData && !catalog?.demo_enabled) {
      if (catalog?.bot_url) openSource(catalog.bot_url);
      else setError("Для входа откройте мини-приложение через бота MAX.");
      return;
    }
    await run(async () => {
      const result = await api.login(window.WebApp?.initData);
      session.set(result.token);
      setMe(result.user);
      setEditing(true);
      await refresh();
    });
  }
  function requireProfile() {
    if (!me) {
      void login();
      return false;
    }
    if (!me.profile.consent || !me.profile.program_ids.length) {
      setEditing(true);
      return false;
    }
    return true;
  }
  function add(o: Olympiad) {
    if (!requireProfile()) return;
    void run(async () => {
      const r = await api.add(o.id);
      setTrack(r.items);
      setToast("Олимпиада добавлена в маршрут");
    });
  }
  function change(id: string, status?: string) {
    void run(async () => {
      const r = status ? await api.update(id, status) : await api.remove(id);
      setTrack(r.items);
      await refresh();
      setToast(status ? "Статус обновлён" : "Олимпиада удалена из маршрута");
    });
  }
  function save(profile: Profile) {
    void run(async () => {
      const user = await api.save(profile);
      setMe(user);
      setEditing(false);
      setToast("Маршрут настроен. Выбирай олимпиады!");
    });
  }
  function demo(id: string, kind: "registration" | "rule_change") {
    void run(async () => {
      await api.demo(id, kind);
      await refresh();
      setTab("notifications");
      setToast(
        me?.is_demo
          ? "Пример уведомления готов"
          : "Тестовое сообщение поставлено в очередь MAX",
      );
    });
  }
  const selectedPrograms =
    catalog?.programs.filter((p) => me?.profile.program_ids.includes(p.id)) ||
    [];
  const entries =
    catalog?.olympiads.filter((o) =>
      track.some((t) => t.olympiad_id === o.id),
    ) || [];
  const benefitCount = (o: Olympiad) =>
    o.benefits.filter(
      (b) =>
        b.kind !== "unknown" &&
        (!selectedPrograms.length ||
          selectedPrograms.some((p) => p.id === b.program_id)),
    ).length;
  const visible =
    catalog?.olympiads
      .filter(
        (o) =>
          (subject === "all" || o.subject === subject) &&
          `${o.name} ${o.profile}`
            .toLowerCase()
            .includes(query.toLowerCase()) &&
          (!onlyRelevant ||
            (benefitCount(o) > 0 &&
              (!me ||
                (o.grades.includes(me.profile.grade) &&
                  me.profile.subjects.includes(o.subject))))),
      )
      .sort((a, b) => benefitCount(b) - benefitCount(a)) || [];
  const tz = me?.profile.timezone || "Europe/Moscow";
  const calendarEvents = entries
    .flatMap((o) => o.events.map((e) => ({ ...e, olympiad: o })))
    .sort(
      (a, b) =>
        (a.deadline ? Date.parse(a.deadline) : Infinity) -
        (b.deadline ? Date.parse(b.deadline) : Infinity),
    );
  const futureEvents = calendarEvents.filter(
    (e) => e.deadline && Date.parse(e.deadline) > now,
  );
  const conflicts = new Set(
    futureEvents
      .filter((e) =>
        futureEvents.some(
          (other) =>
            other.olympiad.id !== e.olympiad.id &&
            other.deadline === e.deadline,
        ),
      )
      .map((e) => e.olympiad.id),
  );

  function card(o: Olympiad) {
    const item = track.find((t) => t.olympiad_id === o.id);
    const state = registration(o, now);
    return (
      <article className="olympiad-card" key={o.id}>
        <div className="card-top">
          <span className={`subject-icon ${o.subject}`}>
            <span>{o.subject === "math" ? "∑" : "</>"}</span>
          </span>
          <div className="card-tags">
            <span className="tag">{subjects[o.subject]}</span>
            <span className={`status-dot ${state.closed ? "closed" : ""}`}>
              {state.label}
            </span>
          </div>
        </div>
        <button className="card-title" onClick={() => setDetail(o)}>
          <small>{o.name}</small>
          <h3>
            {o.profile}
            <Icon name="external" size={17} />
          </h3>
        </button>
        <p className="card-description">{o.description}</p>
        <div className="benefit-line">
          <Icon name="book" size={17} />
          <span>
            {benefitCount(o)
              ? `БВИ в правилах 2026 · ${benefitCount(o)} ${benefitCount(o) === 1 ? "цель" : "цели"}`
              : "Условия льгот требуют проверки"}
          </span>
        </div>
        <div className="card-footer">
          <button className="text-button" onClick={() => setDetail(o)}>
            Условия и сроки <Icon name="arrow" size={16} />
          </button>
          <button
            className={`add-button ${item ? "added" : ""}`}
            disabled={busy}
            onClick={() => (item ? setTab("track") : add(o))}
            aria-label={
              item
                ? `Открыть маршрут: ${o.profile}`
                : `Добавить в маршрут: ${o.name}, ${o.profile}`
            }
          >
            <Icon name={item ? "check" : "plus"} size={18} />
            {item ? "В маршруте" : "В маршрут"}
          </button>
        </div>
      </article>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setTab("discover");
          }}
        >
          <span className="brand-mark">
            <Icon name="route" size={26} />
          </span>
          <span>
            маршрут<span className="brand-caption">ОЛИМПИАДНЫЙ НАВИГАТОР</span>
          </span>
        </a>
        <span className="nav-caption">ТВОЯ ТРАЕКТОРИЯ</span>
        <nav aria-label="Основная навигация">
          {tabs.map((t) => (
            <button
              key={t.id}
              className={`nav-item ${tab === t.id ? "active" : ""}`}
              onClick={() => setTab(t.id)}
              aria-current={tab === t.id ? "page" : undefined}
            >
              <Icon name={t.icon} />
              <span>{t.label}</span>
              {t.id === "track" && track.length > 0 && <b>{track.length}</b>}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="small-symbol">↗</span>
          <strong>
            Большая цель.
            <br />
            Понятные шаги.
          </strong>
          <p>От первой олимпиады до осознанного выбора вуза.</p>
          <span className="max-label">
            Вместе с MAX <span>↗</span>
          </span>
        </div>
        <div className="sidebar-bottom">
          <span className="avatar">
            <Icon name="user" size={18} />
          </span>
          <div>
            <strong>
              {me ? `${me.profile.grade} класс` : "Твой будущий маршрут"}
            </strong>
            <small>
              {me
                ? `Поступление в ${me.profile.admission_year}`
                : "Начинается с одной цели"}
            </small>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <span className="mobile-brand">
              <Icon name="route" /> маршрут
            </span>
            <span className="breadcrumb">
              Твоя траектория <span>/</span>{" "}
              {tabs.find((t) => t.id === tab)?.label}
            </span>
          </div>
          <div className="topbar-right">
            <span className="season">СЕЗОН 2026 / 27</span>
            <button
              className="icon-button"
              aria-label="Открыть напоминания"
              onClick={() => setTab("notifications")}
            >
              <Icon name="bell" />
              <i
                className={
                  me?.profile.notifications_enabled ? "notification-dot" : ""
                }
              />
            </button>
          </div>
        </header>
        <main>
          {error && (
            <div role="alert" className="error-banner">
              <Icon name="info" />
              <span>{error}</span>
              <button
                onClick={() => {
                  void load();
                }}
              >
                Повторить
              </button>
              <button aria-label="Закрыть ошибку" onClick={() => setError("")}>
                <Icon name="close" size={16} />
              </button>
            </div>
          )}
          {loading ? (
            <div className="loading">
              <span className="spinner" />
              <h2>Собираем твой маршрут…</h2>
            </div>
          ) : !catalog ? (
            <div className="empty">
              <Icon name="compass" size={42} />
              <h2>Не удалось загрузить каталог</h2>
              <button
                className="button primary"
                onClick={() => {
                  void load();
                }}
              >
                Попробовать ещё раз
              </button>
            </div>
          ) : (
            <>
              {me?.is_demo && (
                <div className="demo-strip">
                  <span>Демонстрационный профиль</span>
                  <span>
                    Данные сохраняются. Сообщения MAX показываются в виде
                    примера.
                  </span>
                </div>
              )}
              {tab === "discover" && (
                <>
                  <section className="hero">
                    <div className="hero-copy">
                      <span className="eyebrow">
                        <i /> ТВОЙ СЛЕДУЮЩИЙ ШАГ
                      </span>
                      <h1>
                        Большие планы
                        <br />
                        начинаются <em>с маршрута.</em>
                      </h1>
                      <p>
                        Выбирай олимпиады под свою цель в вузе.
                        <br />А мы поможем разобраться в условиях и сроках.
                      </p>
                      <button
                        className="button dark"
                        disabled={
                          busy ||
                          (!me &&
                            !catalog.demo_enabled &&
                            !window.WebApp?.initData)
                        }
                        onClick={() => (me ? setEditing(true) : void login())}
                      >
                        {me?.profile.consent
                          ? "Изменить мои цели"
                          : window.WebApp?.initData
                            ? "Выбрать свою цель"
                            : "Собрать маршрут"}
                        <Icon name="arrow" size={18} />
                      </button>
                      {!me &&
                        !catalog.demo_enabled &&
                        !window.WebApp?.initData && (
                          <p className="small">
                            Для начала откройте приложение через бота MAX.
                          </p>
                        )}
                    </div>
                    <div className="route-art" aria-hidden="true">
                      <div className="orbit orbit-one" />
                      <div className="orbit orbit-two" />
                      <div className="art-line" />
                      <div className="art-card start-card">
                        <span className="art-icon">✦</span>
                        <span>
                          <small>ТОЧКА СТАРТА</small>
                          <strong>Твой интерес</strong>
                        </span>
                        <i>01</i>
                      </div>
                      <div className="art-card olymp-card">
                        <span className="art-icon blue">∑</span>
                        <span>
                          <small>ПО ПУТИ К ЦЕЛИ</small>
                          <strong>Твоя олимпиада</strong>
                        </span>
                        <span className="mini-check">✓</span>
                      </div>
                      <div className="art-card goal-card">
                        <span className="art-icon orange">↗</span>
                        <span>
                          <small>ТОЧКА НАЗНАЧЕНИЯ</small>
                          <strong>Твой университет</strong>
                        </span>
                      </div>
                      <span className="art-spark">✳</span>
                    </div>
                  </section>
                  <section className="goals-strip">
                    <div>
                      <span className="mini-icon">
                        <Icon name="compass" />
                      </span>
                      <div>
                        <h3>
                          {selectedPrograms.length
                            ? "Твои цели"
                            : "Сначала — направление"}
                        </h3>
                        <p>
                          {selectedPrograms.length
                            ? "НИУ ВШЭ · Москва"
                            : "Две программы ВШЭ для первого маршрута"}
                        </p>
                      </div>
                    </div>
                    <div className="goal-chips">
                      {selectedPrograms.length ? (
                        selectedPrograms.map((p) => (
                          <button key={p.id} onClick={() => setEditing(true)}>
                            {p.short_name}
                            <Icon name="check" size={14} />
                          </button>
                        ))
                      ) : (
                        <button
                          onClick={() => (me ? setEditing(true) : void login())}
                          disabled={busy || (!me && !catalog.demo_enabled)}
                        >
                          Выбрать программы <Icon name="plus" size={16} />
                        </button>
                      )}
                    </div>
                  </section>
                  <div className="section-heading">
                    <div>
                      <span className="eyebrow">ВОЗМОЖНОСТИ ДЛЯ ТЕБЯ</span>
                      <h2>
                        Найди свою олимпиаду <span>{visible.length}</span>
                      </h2>
                    </div>
                    <span className="small muted">
                      9–11 классы · математика и IT
                    </span>
                  </div>
                  <div className="catalog-toolbar">
                    <div className="filter-tabs" aria-label="Предмет">
                      {[
                        ["all", "Все предметы"],
                        ["math", "Математика"],
                        ["informatics", "Информатика"],
                      ].map(([id, label]) => (
                        <button
                          key={id}
                          className={subject === id ? "active" : ""}
                          onClick={() => setSubject(id)}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                    <label className="search">
                      <Icon name="search" size={18} />
                      <input
                        aria-label="Поиск олимпиад"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Название или профиль"
                      />
                    </label>
                  </div>
                  <label className="relevant">
                    <input
                      type="checkbox"
                      checked={onlyRelevant}
                      onChange={(e) => setOnlyRelevant(e.target.checked)}
                    />
                    С известными льготами для моих целей и предметов
                  </label>
                  <div className="cards-grid">{visible.map(card)}</div>
                  {!visible.length && (
                    <div className="empty">
                      <Icon name="search" size={32} />
                      <h3>По этим условиям ничего не нашли</h3>
                      <p>Попробуй другой предмет или сбрось фильтры.</p>
                      <button
                        className="text-button"
                        onClick={() => {
                          setQuery("");
                          setSubject("all");
                          setOnlyRelevant(false);
                        }}
                      >
                        Сбросить фильтры
                      </button>
                    </div>
                  )}
                  <div className="source-note">
                    <Icon name="info" size={19} />
                    <p>
                      У каждой возможности — свой источник. Правила приёма 2026
                      года служат ориентиром: для поступления в{" "}
                      {me?.profile.admission_year || 2027} условия ещё нужно
                      проверить.
                    </p>
                  </div>
                </>
              )}
              {tab === "track" && (
                <>
                  <PageTitle
                    eyebrow="ОТ ЦЕЛИ К ДЕЙСТВИЮ"
                    title="Мой маршрут"
                    text="Здесь только то, что ты выбрал. Двигайся в своём темпе."
                  />
                  <div className="stats">
                    <div>
                      <strong>{entries.length}</strong>
                      <span>олимпиад в плане</span>
                    </div>
                    <div>
                      <strong>
                        {track.filter((t) => t.status === "registered").length}
                      </strong>
                      <span>регистраций отмечено</span>
                    </div>
                    <div>
                      <strong>{selectedPrograms.length}</strong>
                      <span>целевых программ</span>
                    </div>
                  </div>
                  {!entries.length ? (
                    <Empty
                      title="Первый шаг — выбрать олимпиаду"
                      text="Добавь интересующие профили из каталога. Здесь появятся твой план и следующие действия."
                      action={() => setTab("discover")}
                    />
                  ) : (
                    <>
                      {selectedPrograms.map((p) => (
                        <div className="coverage" key={p.id}>
                          <Icon name="book" />
                          <span>{p.name}</span>
                          <b>
                            {entries.some((o) =>
                              o.benefits.some(
                                (b) =>
                                  b.program_id === p.id && b.kind === "bvi",
                              ),
                            )
                              ? "Есть ориентир БВИ на 2026"
                              : "Нет проверенной связи"}
                          </b>
                        </div>
                      ))}
                      <div className="track-list">
                        {entries.map((o) => {
                          const item = track.find(
                            (t) => t.olympiad_id === o.id,
                          )!;
                          return (
                            <article className="track-card" key={o.id}>
                              <div className="track-card-heading">
                                <span className={`subject-icon ${o.subject}`}>
                                  {o.subject === "math" ? "∑" : "</>"}
                                </span>
                                <div>
                                  <small>{o.name}</small>
                                  <h3>{o.profile}</h3>
                                </div>
                                <span
                                  className={`tag ${item.status === "registered" ? "green" : ""}`}
                                >
                                  {statuses[item.status]}
                                </span>
                              </div>
                              <div className="progress-line">
                                {["В плане", "Регистрация", "Участие"].map(
                                  (label, i) => (
                                    <span
                                      className={
                                        i <=
                                        [
                                          "planned",
                                          "registered",
                                          "completed",
                                        ].indexOf(item.status)
                                          ? "done"
                                          : ""
                                      }
                                      key={label}
                                    >
                                      <i>{i + 1}</i>
                                      {label}
                                    </span>
                                  ),
                                )}
                              </div>
                              <p className="muted">
                                {item.status === "completed"
                                  ? "Участие отмечено. Эта отметка не подтверждает получение диплома."
                                  : o.kind === "vsosh"
                                    ? "Ближайший шаг: уточни у координатора своей школы дату и порядок участия."
                                    : registration(o, now).closed
                                      ? "Общая регистрация закрыта. Если ты уже зарегистрировался, отметь это и проверь расписание этапа."
                                      : "Ближайший шаг: проверь официальный сайт и зарегистрируйся."}
                              </p>
                              <div className="track-actions">
                                <button
                                  className="button secondary"
                                  onClick={() => setDetail(o)}
                                >
                                  Условия и сроки
                                </button>
                                <label className="status-select">
                                  Мой статус
                                  <select
                                    aria-label={`Статус: ${o.name}, ${o.profile}`}
                                    value={item.status}
                                    disabled={busy}
                                    onChange={(e) =>
                                      change(o.id, e.target.value)
                                    }
                                  >
                                    {Object.entries(statuses).map(
                                      ([value, label]) => (
                                        <option key={value} value={value}>
                                          {label}
                                        </option>
                                      ),
                                    )}
                                  </select>
                                </label>
                                <button
                                  className="text-button danger"
                                  disabled={busy}
                                  onClick={() => change(o.id)}
                                >
                                  Убрать
                                </button>
                              </div>
                              {catalog.demo_enabled && (
                                <details className="demo-controls">
                                  <summary>
                                    Проверить напоминания · тестовые события
                                  </summary>
                                  <p>
                                    Реальные сроки и правила останутся прежними.
                                    В MAX сообщение придёт с учётом тихих часов.
                                  </p>
                                  <div>
                                    <button
                                      disabled={
                                        busy || item.status !== "planned"
                                      }
                                      onClick={() => demo(o.id, "registration")}
                                    >
                                      Тест регистрации
                                    </button>
                                    <button
                                      disabled={
                                        busy || item.status === "completed"
                                      }
                                      onClick={() => demo(o.id, "rule_change")}
                                    >
                                      Тест изменения правила
                                    </button>
                                  </div>
                                </details>
                              )}
                            </article>
                          );
                        })}
                      </div>
                    </>
                  )}
                </>
              )}
              {tab === "calendar" && (
                <>
                  <PageTitle
                    eyebrow="НЕ ПРОПУСТИ СВОЙ ШАНС"
                    title="Календарь маршрута"
                    text={`Сроки выбранных олимпиад · ${tz}. Если дата неизвестна, мы не подставляем примерную.`}
                  />
                  {!entries.length ? (
                    <Empty
                      title="Добавь события в свой календарь"
                      text="Выбери олимпиаду — её опубликованные этапы появятся здесь автоматически."
                      action={() => setTab("discover")}
                    />
                  ) : (
                    <div className="timeline">
                      {calendarEvents.map((e) => (
                        <article
                          className="timeline-event"
                          key={`${e.olympiad.id}-${e.id}`}
                        >
                          <span className="timeline-point" />
                          <div className="event-date">
                            {e.deadline
                              ? date(e.deadline, tz)
                              : "Дата уточняется"}
                            {e.deadline && Date.parse(e.deadline) < now && (
                              <span className="tag">Срок прошёл</span>
                            )}
                            {conflicts.has(e.olympiad.id) && (
                              <span className="tag orange-tag">
                                Пересечение сроков
                              </span>
                            )}
                          </div>
                          <div>
                            <small>
                              {e.olympiad.name} · {e.olympiad.profile}
                            </small>
                            <h3>{e.title}</h3>
                            <p className="muted">{e.source.note}</p>
                            <button
                              className="text-button"
                              onClick={() => openSource(e.source.url)}
                            >
                              Проверить у организатора{" "}
                              <Icon name="external" size={15} />
                            </button>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </>
              )}
              {tab === "notifications" && (
                <>
                  <PageTitle
                    eyebrow="ВАЖНОЕ — ВОВРЕМЯ"
                    title="Напоминания"
                    text="Конкретное событие, понятное действие. Всё связано с твоим маршрутом."
                  />
                  <div className="notification-settings">
                    <span className="mini-icon">
                      <Icon name="bell" />
                    </span>
                    <div>
                      <strong>
                        {me?.profile.notifications_enabled
                          ? "Напоминания включены"
                          : "Напоминания пока отключены"}
                      </strong>
                      <p>
                        {me
                          ? `Тихие часы: ${me.profile.quiet_start}:00–${me.profile.quiet_end}:00 · ${tz}`
                          : "Войди и настрой удобное время."}
                      </p>
                    </div>
                    <button
                      className="text-button"
                      onClick={() => (me ? setEditing(true) : void login())}
                    >
                      Настроить <Icon name="arrow" size={16} />
                    </button>
                  </div>
                  {notifications.length === 0 ? (
                    <Empty
                      title="Здесь будет только важное"
                      text="Добавь олимпиады в маршрут и включи напоминания. Для проверки доступно тестовое событие в карточке маршрута."
                      action={() => setTab("track")}
                      label="К моему маршруту"
                    />
                  ) : (
                    <div className="message-list">
                      {notifications.map((n) => (
                        <article className="message-card" key={n.id}>
                          <div className="message-meta">
                            <span className="tag">
                              {n.is_demo
                                ? "ТЕСТОВОЕ СОБЫТИЕ"
                                : "СОБЫТИЕ МАРШРУТА"}
                            </span>
                            <span>{delivery[n.state] || n.state}</span>
                          </div>
                          <h3>{n.title}</h3>
                          <p>{n.text}</p>
                          <small>
                            {date(n.due_at, tz)}
                            {n.error && ` · ${n.error}`}
                          </small>
                          {["preview", "sent"].includes(n.state) && (
                            <div className="message-actions">
                              {(n.kind === "registration"
                                ? [
                                    ["registered", "Я зарегистрировался"],
                                    ["snooze", "Через час"],
                                    ["remove", "Убрать из трека"],
                                  ]
                                : [
                                    ["read", "Ознакомился"],
                                    ["snooze", "Через час"],
                                  ]
                              ).map(([action, label]) => (
                                <button
                                  key={action}
                                  disabled={busy}
                                  onClick={() =>
                                    void run(async () => {
                                      await api.action(n.id, action);
                                      await refresh();
                                      setToast("Действие сохранено");
                                    })
                                  }
                                >
                                  {label}
                                </button>
                              ))}
                            </div>
                          )}
                        </article>
                      ))}
                    </div>
                  )}
                </>
              )}
              {tab === "profile" && (
                <>
                  <PageTitle
                    eyebrow="МАРШРУТ ПОД ТЕБЯ"
                    title="Мой профиль"
                    text="Цель можно поменять. Твой план и отметки сохранятся."
                  />
                  {me ? (
                    <div className="profile-panel">
                      <ProfileForm
                        key={me.id}
                        initial={me.profile}
                        catalog={catalog}
                        save={save}
                        busy={busy}
                        isDemo={me.is_demo}
                      />
                      <div className="delete-zone">
                        <h3>Твои данные под твоим контролем</h3>
                        <p>
                          Удаление очистит профиль, маршрут, историю сообщений и
                          все сессии.
                        </p>
                        <button
                          className="text-button danger"
                          onClick={() => setDeleting(true)}
                        >
                          Удалить профиль
                        </button>
                      </div>
                    </div>
                  ) : (
                    <Empty
                      title="Начнём с твоей цели"
                      text="Нужны только класс, год поступления и интересующие программы."
                      action={() => void login()}
                      label="Создать профиль"
                    />
                  )}
                </>
              )}
              <footer className="page-footer">
                <span>
                  маршрут <i>·</i> шаг за шагом к своему вузу
                </span>
                <span>Проверка источников: {catalog.snapshot_date}</span>
              </footer>
            </>
          )}
        </main>
      </div>
      {toast && (
        <div role="status" className="toast">
          <Icon name="check" />
          {toast}
        </div>
      )}
      {editing && me && catalog && (
        <Dialog
          error={error}
          title="Настроим твой маршрут"
          close={() => setEditing(false)}
        >
          <ProfileForm
            initial={me.profile}
            catalog={catalog}
            save={save}
            busy={busy}
            isDemo={me.is_demo}
          />
        </Dialog>
      )}
      {deleting && (
        <Dialog
          error={error}
          title="Удалить профиль?"
          close={() => setDeleting(false)}
        >
          <p>
            Трек, отметки и история будут удалены. Напоминания остановятся. Это
            действие нельзя отменить.
          </p>
          <div className="dialog-actions">
            <button
              className="button secondary"
              onClick={() => setDeleting(false)}
            >
              Сохранить профиль
            </button>
            <button
              className="button destructive"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  await api.delete();
                  session.clear();
                  setMe(null);
                  setTrack([]);
                  setNotifications([]);
                  setDeleting(false);
                  setTab("discover");
                  setToast("Профиль удалён");
                })
              }
            >
              Удалить
            </button>
          </div>
        </Dialog>
      )}
      {detail && catalog && (
        <Dialog
          error={error}
          title={detail.profile}
          close={() => setDetail(null)}
        >
          <div className="detail-intro">
            <span className="tag">
              {detail.kind === "vsosh" ? "ВсОШ" : "Перечневая олимпиада"}
            </span>
            <span className="tag">{detail.grades.join(", ")} классы</span>
            <h3>{detail.name}</h3>
            <p>{detail.description}</p>
          </div>
          <div className="notice">
            <Icon name="info" />
            <span>
              Условия ниже относятся к приёму 2026 года. Они не подтверждают
              льготу при поступлении в {me?.profile.admission_year || 2027}{" "}
              году. БВИ и 100 баллов — разные льготы.
            </span>
          </div>
          <h3>Какие возможности открывает</h3>
          {detail.benefits
            .filter(
              (b) =>
                !selectedPrograms.length ||
                selectedPrograms.some((p) => p.id === b.program_id),
            )
            .map((b) => (
              <div className="benefit-detail" key={b.program_id}>
                <div>
                  <strong>
                    {catalog.programs.find((p) => p.id === b.program_id)?.name}
                  </strong>
                  <span
                    className={`tag ${b.kind !== "unknown" ? "green" : ""}`}
                  >
                    {b.kind === "bvi"
                      ? "БВИ · 2026"
                      : b.kind === "100"
                        ? "100 баллов · 2026"
                        : "Нужна проверка"}
                  </span>
                </div>
                <dl>
                  <dt>Результат</dt>
                  <dd>{b.result}</dd>
                  <dt>Подтверждение</dt>
                  <dd>{b.confirmation}</dd>
                </dl>
                <p className="small muted">{b.explanation}</p>
                <button
                  className="text-button"
                  onClick={() => openSource(b.source.url)}
                >
                  Официальное правило <Icon name="external" size={15} />
                </button>
                <small className="source-caption">
                  {b.source.note} Проверено: {b.source.checked_at}
                </small>
              </div>
            ))}
          <h3>Сроки и ближайшие действия</h3>
          {detail.events.map((e) => (
            <div className="detail-event" key={e.id}>
              <Icon name="calendar" />
              <div>
                <strong>{e.title}</strong>
                <p>
                  {e.deadline
                    ? date(e.deadline, tz)
                    : "Точная дата ещё не проверена"}
                </p>
                <small>{e.source.note}</small>
              </div>
            </div>
          ))}
          <div className="dialog-actions">
            <button
              className="button secondary"
              onClick={() => openSource(detail.registration_url)}
            >
              Сайт организатора <Icon name="external" size={16} />
            </button>
            <button
              className="button primary"
              disabled={busy || track.some((t) => t.olympiad_id === detail.id)}
              onClick={() => {
                const item = detail;
                setDetail(null);
                add(item);
              }}
            >
              {track.some((t) => t.olympiad_id === detail.id)
                ? "Уже в маршруте"
                : "Добавить в маршрут"}
              <Icon name="plus" size={18} />
            </button>
          </div>
        </Dialog>
      )}
    </div>
  );
}

function PageTitle({
  eyebrow,
  title,
  text,
}: {
  eyebrow: string;
  title: string;
  text: string;
}) {
  return (
    <div className="page-title">
      <span className="eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      <p>{text}</p>
    </div>
  );
}
function Empty({
  title,
  text,
  action,
  label = "Найти олимпиаду",
}: {
  title: string;
  text: string;
  action: () => void;
  label?: string;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Icon name="route" size={34} />
      </span>
      <h2>{title}</h2>
      <p>{text}</p>
      <button className="button primary" onClick={action}>
        {label}
        <Icon name="arrow" size={17} />
      </button>
    </div>
  );
}
export default App;
