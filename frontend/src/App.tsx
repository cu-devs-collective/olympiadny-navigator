import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { api, ApiError, openSource, session } from "./route-api";
import type { Catalog, Me, Olympiad, Profile, TrackEntry } from "./route-api";
import { Icon } from "./icons";
import "./App.css";

type Tab = "discover" | "track" | "calendar" | "profile";
const tabs: { id: Tab; label: string; icon: string }[] = [
  { id: "discover", label: "Олимпиады", icon: "grid" },
  { id: "track", label: "Мой маршрут", icon: "route" },
  { id: "calendar", label: "Календарь", icon: "calendar" },
  { id: "profile", label: "Мой профиль", icon: "user" },
];
const subjects = { math: "Математика", informatics: "Информатика" };
const statuses = {
  planned: "В плане",
  registered: "Регистрация отмечена",
  completed: "Участие завершено",
};
const zones = [
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
];
function graduationYear(grade: number) {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: "Europe/Moscow",
    year: "numeric",
    month: "numeric",
  }).formatToParts(new Date());
  const year = Number(parts.find((p) => p.type === "year")!.value);
  const month = Number(parts.find((p) => p.type === "month")!.value);
  return year + (month >= 9 ? 1 : 0) + 11 - grade;
}
const date = (value: string, timezone = "Europe/Moscow") =>
  new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  }).format(new Date(value));
function registration(o: Olympiad, now: number) {
  const e =
    o.events.find(
      (e) =>
        e.kind === "registration" &&
        e.deadline &&
        Date.parse(e.deadline) >= now,
    ) || o.events.find((e) => e.kind === "registration");
  if (!e?.deadline) return { label: "Ждём расписание", open: false };
  if (Date.parse(e.deadline) < now)
    return { label: "Регистрация закрыта", open: false };
  if (e.starts_at && Date.parse(e.starts_at) > now)
    return { label: "Регистрация впереди", open: false };
  return {
    label: `До ${new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short", timeZone: "Europe/Moscow" }).format(new Date(e.deadline))}`,
    open: true,
  };
}
function Dialog({
  title,
  close,
  children,
  error,
}: {
  title: string;
  close: () => void;
  children: ReactNode;
  error?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    d?.showModal();
    return () => d?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className="dialog"
      aria-label={title}
      onCancel={close}
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div className="dialog-head">
        <h2>{title}</h2>
        <button className="icon-button" aria-label="Закрыть" onClick={close}>
          <Icon name="close" />
        </button>
      </div>
      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
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
}: {
  initial: Profile;
  catalog: Catalog;
  save: (p: Profile) => void;
  busy: boolean;
}) {
  const [p, setP] = useState({
    ...initial,
    admission_year: graduationYear(initial.grade),
  });
  function submit(e: FormEvent) {
    e.preventDefault();
    save({ ...p, admission_year: graduationYear(p.grade) });
  }
  return (
    <form className="profile-form" onSubmit={submit}>
      <div className="form-grid">
        <label>
          Сейчас учусь в
          <select
            value={p.grade}
            onChange={(e) =>
              setP({
                ...p,
                grade: +e.target.value,
                admission_year: graduationYear(+e.target.value),
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
          <input
            aria-label="Год поступления"
            value={p.admission_year}
            readOnly
          />
          <small>После окончания 11 класса</small>
        </label>
      </div>
      <fieldset>
        <legend>Куда хочешь поступить?</legend>
        <p className="muted">Выбери одну или две программы.</p>
        <div className="program-options">
          {catalog.programs.map((program) => (
            <label
              key={program.id}
              className={`program-option ${p.program_ids.includes(program.id) ? "selected" : ""}`}
            >
              <input
                type="checkbox"
                checked={p.program_ids.includes(program.id)}
                disabled={
                  !p.program_ids.includes(program.id) &&
                  p.program_ids.length >= 2
                }
                onChange={() =>
                  setP({
                    ...p,
                    program_ids: p.program_ids.includes(program.id)
                      ? p.program_ids.filter((id) => id !== program.id)
                      : [...p.program_ids, program.id],
                  })
                }
              />
              <span>
                <small>
                  {program.university} · {program.campus}
                </small>
                <strong>{program.name}</strong>
                <small>{program.description}</small>
              </span>
            </label>
          ))}
        </div>
      </fieldset>
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
      <label>
        Часовой пояс
        <select
          value={p.timezone}
          onChange={(e) => setP({ ...p, timezone: e.target.value })}
        >
          {zones.map((z) => (
            <option key={z}>{z}</option>
          ))}
        </select>
      </label>
      <p className="inline-note">
        Сроки и действия приходят в чат MAX. Включить сообщения и настроить
        тихие часы можно командой /settings.
      </p>
      <label className="consent">
        <input
          type="checkbox"
          checked={p.consent}
          onChange={(e) => setP({ ...p, consent: e.target.checked })}
        />
        <span>
          Разрешаю сохранять класс, цели, настройки и отметки для работы
          маршрута. При входе через MAX — также его идентификатор. Профиль можно
          удалить вместе с историей.
        </span>
      </label>
      <button
        className="button primary"
        disabled={
          busy || !p.consent || !p.program_ids.length || !p.subjects.length
        }
      >
        {busy ? "Сохраняем…" : "Сохранить мой маршрут"}
      </button>
    </form>
  );
}
function App() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [track, setTrack] = useState<TrackEntry[]>([]);
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
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 60000);
    return () => clearInterval(timer);
  }, []);
  const refresh = useCallback(async () => {
    const [u, t] = await Promise.all([api.me(), api.track()]);
    setMe(u);
    setTrack(t.items);
  }, []);
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setCatalog(await api.catalog());
      window.WebApp?.ready?.();
      if (window.WebApp?.initData) {
        const r = await api.login(window.WebApp.initData);
        session.set(r.token);
      }
      if (session.get()) await refresh();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) session.clear();
      setError(e instanceof Error ? e.message : "Не удалось загрузить каталог");
    } finally {
      setLoading(false);
    }
  }, [refresh]);
  useEffect(() => {
    const t = setTimeout(() => void load(), 0);
    return () => clearTimeout(t);
  }, [load]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 4000);
    return () => clearTimeout(t);
  }, [toast]);
  useEffect(() => {
    if (!me?.id) return;
    const sync = () => {
      if (!document.hidden) void refresh().catch(() => {});
    };
    const t = setInterval(sync, 15000);
    window.addEventListener("focus", sync);
    document.addEventListener("visibilitychange", sync);
    return () => {
      clearInterval(t);
      window.removeEventListener("focus", sync);
      document.removeEventListener("visibilitychange", sync);
    };
  }, [me?.id, refresh]);
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
      return;
    }
    await run(async () => {
      const r = await api.login(window.WebApp?.initData);
      session.set(r.token);
      setMe(r.user);
      setEditing(true);
      await refresh();
    });
  }
  function add(o: Olympiad) {
    if (!me) {
      void login();
      return;
    }
    if (!me.profile.consent || !me.profile.program_ids.length) {
      setEditing(true);
      return;
    }
    void run(async () => {
      setTrack((await api.add(o.id)).items);
      setToast("Добавлено в маршрут");
    });
  }
  function change(id: string, status?: string) {
    void run(async () => {
      setTrack(
        (status ? await api.update(id, status) : await api.remove(id)).items,
      );
      setToast(status ? "Статус обновлён" : "Удалено из маршрута");
    });
  }
  function save(p: Profile) {
    void run(async () => {
      setMe(await api.save(p));
      setEditing(false);
      setToast("Профиль сохранён");
    });
  }
  const selected =
    catalog?.programs.filter((p) => me?.profile.program_ids.includes(p.id)) ||
    [];
  const entries =
    catalog?.olympiads.filter((o) =>
      track.some((t) => t.olympiad_id === o.id),
    ) || [];
  const benefits = (o: Olympiad) =>
    o.benefits.filter(
      (b) => !selected.length || selected.some((p) => p.id === b.program_id),
    );
  const visible =
    catalog?.olympiads.filter(
      (o) =>
        (subject === "all" || o.subject === subject) &&
        `${o.name} ${o.profile}`.toLowerCase().includes(query.toLowerCase()) &&
        (!onlyRelevant ||
          !me ||
          (o.grades.includes(me.profile.grade) &&
            me.profile.subjects.includes(o.subject))),
    ) || [];
  const tz = me?.profile.timezone || "Europe/Moscow";
  const events = entries
    .flatMap((o) => o.events.map((e) => ({ ...e, olympiad: o })))
    .sort(
      (a, b) =>
        Date.parse(a.deadline || a.starts_at || "9999-01-01") -
        Date.parse(b.deadline || b.starts_at || "9999-01-01"),
    );
  function reset() {
    setQuery("");
    setSubject("all");
    setOnlyRelevant(false);
  }
  function card(o: Olympiad, inTrack = false) {
    const item = track.find((t) => t.olympiad_id === o.id),
      state = registration(o, now);
    const verified = benefits(o).filter((b) => b.kind !== "unknown");
    return (
      <article className="olympiad-card" key={o.id}>
        <div className="card-top">
          <span className={`subject-mark ${o.subject}`}>
            {o.subject === "math" ? "∑" : "{ }"}
          </span>
          <span className={`status ${state.open ? "open" : ""}`}>
            {state.label}
          </span>
        </div>
        <div className="card-title">
          <span className="muted">{o.name}</span>
          <h2>{o.profile}</h2>
        </div>
        <p className="card-description">{o.description}</p>
        <div className="card-facts">
          <span>{o.kind === "vsosh" ? "ВсОШ" : "Олимпиада вуза"}</span>
          <span>
            {o.grades[0]}–{o.grades.at(-1)} классы
          </span>
        </div>
        <div className="benefit-label">
          <Icon name="book" size={16} />
          {verified.length
            ? `Есть льготы в правилах 2026 · ${verified.length}`
            : "Льготы требуют проверки"}
        </div>
        {inTrack && item && (
          <label className="track-status">
            Статус
            <select
              aria-label={`Статус: ${o.name}, ${o.profile}`}
              value={item.status}
              disabled={busy}
              onChange={(e) => change(o.id, e.target.value)}
            >
              {Object.entries(statuses).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
        )}
        <div className="card-footer">
          <button className="text-button" onClick={() => setDetail(o)}>
            Условия и сроки <Icon name="arrow" size={16} />
          </button>
          {inTrack ? (
            <button
              className="icon-button"
              aria-label={`Удалить из маршрута: ${o.name}, ${o.profile}`}
              disabled={busy}
              onClick={() => change(o.id)}
            >
              <Icon name="close" size={18} />
            </button>
          ) : (
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
          )}
        </div>
      </article>
    );
  }
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Маршрут — главная">
          <span className="brand-mark">
            <Icon name="route" size={23} />
          </span>
          <span>
            Маршрут<small>Олимпиады и поступление</small>
          </span>
        </a>
        <div className="topbar-right">
          <span className="max-label">для MAX</span>
          {catalog?.bot_url && (
            <button
              className="button secondary chat-button"
              onClick={() => openSource(catalog.bot_url!)}
            >
              Открыть чат <Icon name="external" size={16} />
            </button>
          )}
        </div>
      </header>
      <div className="workspace">
        <aside className="sidebar">
          <nav aria-label="Основная навигация">
            {tabs.map((t) => (
              <button
                key={t.id}
                className={`nav-item ${tab === t.id ? "active" : ""}`}
                aria-current={tab === t.id ? "page" : undefined}
                onClick={() => {
                  setTab(t.id);
                  setError("");
                }}
              >
                <Icon name={t.icon} />
                <span>{t.label}</span>
                {t.id === "track" && track.length > 0 && <b>{track.length}</b>}
              </button>
            ))}
          </nav>
          <div className="sidebar-context">
            <span className="label">ТВОИ ЦЕЛИ</span>
            {selected.length ? (
              selected.map((p) => (
                <div key={p.id}>
                  <strong>
                    {p.university} · {p.short_name}
                  </strong>
                  <small>{p.campus}</small>
                </div>
              ))
            ) : (
              <p>
                Выбери программы в профиле, чтобы сравнить условия поступления.
              </p>
            )}
            {me && (
              <small>
                {me.profile.grade} класс · поступление{" "}
                {me.profile.admission_year}
              </small>
            )}
          </div>
          <div className="sidebar-chat">
            <strong>Всё срочное — в чате</strong>
            <p>
              Ближайшие сроки, отметки о регистрации и управление сообщениями.
            </p>
            <code>/track · /deadlines</code>
          </div>
        </aside>
        <main>
          {error && (
            <div className="error-banner" role="alert">
              {error}
              <button className="text-button" onClick={() => void load()}>
                Повторить
              </button>
            </div>
          )}
          {loading ? (
            <div className="empty" role="status">
              Загружаем маршрут…
            </div>
          ) : !catalog ? (
            <div className="empty">Каталог пока недоступен.</div>
          ) : (
            <>
              {me?.is_demo && (
                <div className="demo-strip">
                  Браузерное демо · отдельный профиль. Для сообщений и общего
                  маршрута открой приложение из MAX.
                </div>
              )}
              {tab === "discover" && (
                <>
                  <div className="page-heading">
                    <div>
                      <span className="label">СЕЗОН 2026/27</span>
                      <h1>Олимпиады</h1>
                      <p>
                        Выбери предмет, проверь условия и добавь олимпиаду в
                        свой маршрут.
                      </p>
                    </div>
                    {!me ? (
                      <button
                        className="button primary"
                        disabled={busy}
                        onClick={() => void login()}
                      >
                        {catalog.demo_enabled
                          ? "Собрать маршрут"
                          : "Войти через MAX"}
                        <Icon name="plus" size={18} />
                      </button>
                    ) : (
                      <button
                        className="button secondary"
                        onClick={() => setEditing(true)}
                      >
                        Настроить цели
                      </button>
                    )}
                  </div>
                  <div className="catalog-summary">
                    <span>
                      <strong>{catalog.olympiads.length}</strong> профилей
                      олимпиад
                    </span>
                    <span>
                      <strong>{catalog.programs.length}</strong> программы вузов
                    </span>
                    <span>
                      Источники проверены{" "}
                      {(catalog.snapshot_date || "2026-09-30")
                        .split("-")
                        .reverse()
                        .join(".")}
                    </span>
                  </div>
                  <div className="filters">
                    <label className="search">
                      <Icon name="search" size={19} />
                      <input
                        aria-label="Поиск олимпиад"
                        placeholder="Название или предмет"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                      />
                    </label>
                    <div className="segments">
                      {[
                        ["all", "Все"],
                        ["math", "Математика"],
                        ["informatics", "Информатика"],
                      ].map(([v, l]) => (
                        <button
                          key={v}
                          aria-pressed={subject === v}
                          onClick={() => setSubject(v)}
                        >
                          {l}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="result-line">
                    <span>Найдено: {visible.length}</span>
                    {me && (
                      <label>
                        <input
                          type="checkbox"
                          checked={onlyRelevant}
                          onChange={(e) => setOnlyRelevant(e.target.checked)}
                        />
                        Мой класс и предметы
                      </label>
                    )}
                  </div>
                  <div className="catalog-grid">
                    {visible.map((o) => card(o))}
                  </div>
                  {!visible.length && (
                    <div className="empty">
                      <h2>По этим условиям ничего не нашли</h2>
                      <button className="button secondary" onClick={reset}>
                        Сбросить фильтры
                      </button>
                    </div>
                  )}
                  <p className="catalog-footnote">
                    <Icon name="info" size={17} />
                    {catalog.notice} Каталог обновляется вручную; окончательные
                    сроки — на сайте организатора.
                  </p>
                </>
              )}
              {tab === "track" && (
                <>
                  <div className="page-heading">
                    <div>
                      <span className="label">ЛИЧНЫЙ ПЛАН</span>
                      <h1>Мой маршрут</h1>
                      <p>
                        {selected
                          .map((p) => `${p.university} · ${p.short_name}`)
                          .join(" / ") ||
                          "Добавь олимпиады, в которых планируешь участвовать."}
                      </p>
                    </div>
                    <button
                      className="button secondary"
                      onClick={() => setTab("discover")}
                    >
                      Добавить олимпиаду <Icon name="plus" size={18} />
                    </button>
                  </div>
                  <p className="inline-note">
                    Отметки синхронизируются с ботом. Команда /track открывает
                    этот же список в чате; /settings включает сообщения о
                    сроках.
                  </p>
                  {entries.length ? (
                    <div className="catalog-grid">
                      {entries.map((o) => card(o, true))}
                    </div>
                  ) : (
                    <div className="empty">
                      <Icon name="route" size={36} />
                      <h2>Начни с одной олимпиады</h2>
                      <p>
                        В маршруте будут твои этапы и отметки о регистрации.
                      </p>
                      <button
                        className="button primary"
                        onClick={() => setTab("discover")}
                      >
                        Выбрать олимпиаду
                      </button>
                    </div>
                  )}
                </>
              )}
              {tab === "calendar" && (
                <>
                  <div className="page-heading">
                    <div>
                      <span className="label">СРОКИ ТВОЕГО МАРШРУТА</span>
                      <h1>Календарь</h1>
                      <p>
                        Время: {tz}. События без точного срока показаны
                        отдельно.
                      </p>
                    </div>
                  </div>
                  {!events.length ? (
                    <div className="empty">
                      <h2>Пока нет событий</h2>
                      <p>
                        Добавь олимпиаду в маршрут — здесь появится её
                        расписание.
                      </p>
                      <button
                        className="button primary"
                        onClick={() => setTab("discover")}
                      >
                        Выбрать олимпиаду
                      </button>
                    </div>
                  ) : (
                    <div className="event-list">
                      {events.map((e) => {
                        const stamp = e.deadline || e.starts_at;
                        return (
                          <article
                            className={`event-row ${stamp && Date.parse(stamp) < now ? "past" : ""}`}
                            key={`${e.olympiad.id}-${e.id}`}
                          >
                            <div className="event-date">
                              {stamp ? date(stamp, tz) : "Дата уточняется"}
                              {stamp && Date.parse(stamp) < now && (
                                <small>Прошедшее событие</small>
                              )}
                            </div>
                            <div>
                              <h2>{e.title}</h2>
                              <p>
                                {e.olympiad.name} · {e.olympiad.profile}
                              </p>
                              <small>{e.source.note}</small>
                            </div>
                            <button
                              className="icon-button"
                              aria-label={`Источник: ${e.title}`}
                              onClick={() => openSource(e.source.url)}
                            >
                              <Icon name="external" />
                            </button>
                          </article>
                        );
                      })}
                    </div>
                  )}
                </>
              )}
              {tab === "profile" && (
                <>
                  <div className="page-heading">
                    <div>
                      <span className="label">НАСТРОЙКИ МАРШРУТА</span>
                      <h1>Мой профиль</h1>
                      <p>
                        Класс и программы помогают выбрать подходящие олимпиады.
                      </p>
                    </div>
                  </div>
                  {me ? (
                    <>
                      <div className="profile-panel">
                        <ProfileForm
                          key={`${me.id}-${me.profile.grade}-${me.profile.program_ids.join(",")}`}
                          initial={me.profile}
                          catalog={catalog}
                          save={save}
                          busy={busy}
                        />
                      </div>
                      <button
                        className="text-button destructive"
                        onClick={() => setDeleting(true)}
                      >
                        Удалить профиль
                      </button>
                    </>
                  ) : (
                    <div className="empty">
                      <p>Настрой цели, чтобы сохранять маршрут.</p>
                      <button
                        className="button primary"
                        onClick={() => void login()}
                      >
                        Собрать маршрут
                      </button>
                    </div>
                  )}
                </>
              )}
            </>
          )}
          <footer>
            Маршрут <span>Олимпиадный навигатор в MAX</span>
          </footer>
        </main>
      </div>
      {toast && (
        <div className="toast" role="status">
          <Icon name="check" size={18} />
          {toast}
        </div>
      )}
      {editing && me && catalog && (
        <Dialog
          title="Настроим твой маршрут"
          close={() => setEditing(false)}
          error={error}
        >
          <ProfileForm
            initial={me.profile}
            catalog={catalog}
            save={save}
            busy={busy}
          />
        </Dialog>
      )}
      {deleting && (
        <Dialog
          title="Удалить профиль?"
          close={() => setDeleting(false)}
          error={error}
        >
          <p>
            Маршрут, отметки и история будут удалены. Напоминания в чате
            остановятся.
          </p>
          <div className="dialog-actions">
            <button
              className="button secondary"
              onClick={() => setDeleting(false)}
            >
              Отмена
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
          title={`${detail.name} · ${detail.profile}`}
          close={() => setDetail(null)}
          error={error}
        >
          <p>{detail.description}</p>
          <p className="inline-note">
            Условия ниже относятся к приёму 2026 года. Они не подтверждают
            льготу при поступлении в{" "}
            {me?.profile.admission_year || graduationYear(11)} году. БВИ и 100
            баллов — разные льготы.
          </p>
          <h3>Условия поступления</h3>
          {benefits(detail).map((b) => (
            <section className="benefit-detail" key={b.program_id}>
              <div className="benefit-head">
                <strong>
                  {
                    catalog.programs.find((p) => p.id === b.program_id)
                      ?.university
                  }{" "}
                  · {catalog.programs.find((p) => p.id === b.program_id)?.name}
                </strong>
                <span
                  className={`status ${b.kind !== "unknown" ? "open" : ""}`}
                >
                  {b.kind === "bvi"
                    ? "БВИ · 2026"
                    : b.kind === "100"
                      ? "100 баллов · 2026"
                      : "Нужна проверка"}
                </span>
              </div>
              <dl>
                <dt>Диплом</dt>
                <dd>{b.result}</dd>
                <dt>Подтверждение</dt>
                <dd>{b.confirmation}</dd>
              </dl>
              <p className="muted">{b.explanation}</p>
              <button
                className="text-button"
                onClick={() => openSource(b.source.url)}
              >
                Источник <Icon name="external" size={15} />
              </button>
              <small>
                {b.source.note} Проверено: {b.source.checked_at}
              </small>
            </section>
          ))}
          <h3>Сроки и этапы</h3>
          {detail.events.map((e) => (
            <div className="detail-event" key={e.id}>
              <strong>{e.title}</strong>
              <p>
                {e.deadline
                  ? date(e.deadline, tz)
                  : e.starts_at
                    ? date(e.starts_at, tz)
                    : "Точная дата ещё не опубликована"}
              </p>
              <small>{e.source.note}</small>
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
                const o = detail;
                setDetail(null);
                add(o);
              }}
            >
              {track.some((t) => t.olympiad_id === detail.id)
                ? "Уже в маршруте"
                : "Добавить в маршрут"}
            </button>
          </div>
        </Dialog>
      )}
    </div>
  );
}
export default App;
