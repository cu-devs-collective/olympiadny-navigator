import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api, ApiError, openSource, openChat, session } from "./route-api";
import type { Catalog, Me, Olympiad, Profile, TrackEntry } from "./route-api";
import { Icon } from "./icons";
import "./App.css";
import { ProfileForm } from "./ProfileForm";

type Tab = "discover" | "track" | "calendar" | "profile";
const tabs: { id: Tab; label: string; icon: string }[] = [
  { id: "discover", label: "Олимпиады", icon: "grid" },
  { id: "track", label: "Мой навигатор", icon: "route" },
  { id: "calendar", label: "Календарь", icon: "calendar" },
  { id: "profile", label: "Мой профиль", icon: "user" },
];
const statuses = {
  planned: "В плане",
  registered: "Регистрация отмечена",
  completed: "Участие завершено",
};
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
  closable = true,
}: {
  title: string;
  close: () => void;
  children: ReactNode;
  error?: string;
  closable?: boolean;
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
      onCancel={(e) => {
        if (closable) close();
        else e.preventDefault();
      }}
      onClick={(e) => {
        if (closable && e.target === e.currentTarget) close();
      }}
    >
      <div className="dialog-head">
        <h2>{title}</h2>
        {closable && (
          <button className="icon-button" aria-label="Закрыть" onClick={close}>
            <Icon name="close" />
          </button>
        )}
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
  const [removing, setRemoving] = useState<Olympiad | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteConfirmed, setDeleteConfirmed] = useState(false);
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
      if (catalog?.bot_url) openChat(catalog.bot_url);
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
      if (!status) setRemoving(null);
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
        `${o.name} ${o.profile} ${(o.aliases || []).join(" ")}`
          .toLocaleLowerCase("ru")
          .replaceAll("ё", "е")
          .includes(
            query.trim().toLocaleLowerCase("ru").replaceAll("ё", "е"),
          ) &&
        (!onlyRelevant ||
          !me ||
          (o.grades.includes(me.profile.grade) &&
            me.profile.subjects.includes(o.subject))),
    ) || [];
  const tz = me?.profile.timezone || "Europe/Moscow";
  const events = entries
    .flatMap((o) => o.events.map((e) => ({ ...e, olympiad: o })))
    .filter((e) => e.deadline || e.starts_at)
    .sort(
      (a, b) =>
        Date.parse(a.deadline || a.starts_at || "9999-01-01") -
        Date.parse(b.deadline || b.starts_at || "9999-01-01"),
    );
  const undated = entries.filter(
    (o) =>
      !o.events.length || o.events.some((e) => !e.deadline && !e.starts_at),
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
            {o.subject === "math"
              ? "∑"
              : o.subject === "informatics"
                ? "{ }"
                : catalog?.subjects
                    .find((s) => s.id === o.subject)
                    ?.name.slice(0, 2)}
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
        {o.registry_level && (
          <p className="registry-label">
            РСОШ · {o.registry_level} уровень · {o.registry_season}
          </p>
        )}
        {verified.length > 0 && (
          <div className="benefit-label">
            <Icon name="book" size={16} />
            Льготы: {verified.length} · диплом действует 4 года
          </div>
        )}
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
              onClick={() => setRemoving(o)}
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
        <a
          className="brand"
          href="/"
          aria-label="Олимпиадный навигатор — главная"
        >
          <span className="brand-mark">
            <Icon name="route" size={23} />
          </span>
          <span>
            Олимпиадный<small className="brand-name">навигатор</small>
          </span>
        </a>
        <div className="topbar-right">
          <span className="max-label">для MAX</span>
          {catalog?.bot_url && (
            <a
              className="bot-link"
              href={catalog.bot_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {catalog.bot_url.replace(/^https?:\/\//, "")}
            </a>
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
                  Демо-режим. Этот профиль не связан с аккаунтом MAX.
                </div>
              )}
              {tab === "discover" && (
                <>
                  <div className="page-heading">
                    <div>
                      <span className="label">СЕЗОН 2026/27</span>
                      <h1>Олимпиады</h1>
                    </div>
                    {!me ? (
                      <button
                        className="button primary"
                        disabled={busy}
                        onClick={() => void login()}
                      >
                        {catalog.demo_enabled
                          ? "Настроить навигатор"
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
                      Программ вузов: <strong>{catalog.programs.length}</strong>
                    </span>
                    <span>
                      Данные актуальны на{" "}
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
                    <select
                      aria-label="Предмет олимпиады"
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                    >
                      <option value="all">Все предметы</option>
                      {catalog.subjects.map((s) => (
                        <option value={s.id} key={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
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
                </>
              )}
              {tab === "track" && (
                <>
                  <div className="page-heading">
                    <div>
                      <span className="label">ЛИЧНЫЙ ПЛАН</span>
                      <h1>Мой навигатор</h1>
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
                      <p>Даты и время указаны в твоём часовом поясе.</p>
                    </div>
                  </div>
                  {!events.length && !undated.length ? (
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
                  {undated.length > 0 && (
                    <section className="undated-events">
                      <h2>Расписание без точных дат</h2>
                      {undated.map((o) => (
                        <article key={o.id}>
                          <strong>
                            {o.name} · {o.profile}
                          </strong>
                          <p className="muted">
                            {o.kind === "vsosh"
                              ? "Даты школьного и муниципального этапов устанавливают в регионе. Расписание сообщит школьный координатор."
                              : o.events
                                  .filter((e) => !e.deadline && !e.starts_at)
                                  .map((e) => e.title)
                                  .join(". ") ||
                                "Расписание сезона 2026/27 ещё не добавлено."}
                          </p>
                          <button
                            className="text-button"
                            onClick={() => openSource(o.registration_url)}
                          >
                            Расписание организатора{" "}
                            <Icon name="external" size={15} />
                          </button>
                        </article>
                      ))}
                    </section>
                  )}
                </>
              )}
              {tab === "profile" && (
                <>
                  <div className="page-heading">
                    <div>
                      <span className="label">НАСТРОЙКИ МАРШРУТА</span>
                      <h1>Мой профиль</h1>
                    </div>
                  </div>
                  {me?.profile.consent ? (
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
                      <section
                        className="delete-profile-panel"
                        aria-label="Удаление профиля"
                      >
                        <div>
                          <h2>Удаление профиля</h2>
                          <p>
                            Цели, олимпиады и история участия будут удалены без
                            возможности восстановления.
                          </p>
                        </div>
                        <button
                          className="button destructive"
                          onClick={() => {
                            setDeleteConfirmed(false);
                            setDeleting(true);
                          }}
                        >
                          Удалить профиль
                        </button>
                      </section>
                    </>
                  ) : (
                    <div className="empty">
                      <p>Настрой цели, чтобы сохранять маршрут.</p>
                      <button
                        className="button primary"
                        onClick={() => void login()}
                      >
                        Настроить навигатор
                      </button>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </main>
      </div>
      {toast && (
        <div className="toast" role="status">
          <Icon name="check" size={18} />
          {toast}
        </div>
      )}
      {me && !me.profile.consent && (
        <Dialog
          title="Добро пожаловать"
          close={() => {}}
          closable={false}
          error={error}
        >
          <p>
            Для работы навигатора сохраняем класс, цели, настройки и отметки. В
            MAX — также идентификатор аккаунта. Удалить профиль и данные можно в
            приложении.
          </p>
          <div className="dialog-actions">
            <button
              className="button primary"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  setMe(await api.acceptConsent());
                })
              }
            >
              Принимаю
            </button>
          </div>
        </Dialog>
      )}
      {editing && me?.profile.consent && catalog && (
        <Dialog
          title="Настройка навигатора"
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
          <label className="delete-confirmation">
            <input
              type="checkbox"
              checked={deleteConfirmed}
              onChange={(e) => setDeleteConfirmed(e.target.checked)}
            />
            Я понимаю, что восстановить данные не получится
          </label>
          <div className="dialog-actions">
            <button
              className="button secondary"
              onClick={() => setDeleting(false)}
            >
              Отмена
            </button>
            <button
              className="button destructive"
              disabled={busy || !deleteConfirmed}
              onClick={() =>
                void run(async () => {
                  if (!deleteConfirmed) return;
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
      {removing && (
        <Dialog
          title="Убрать олимпиаду?"
          close={() => setRemoving(null)}
          error={error}
        >
          <p>
            {removing.name} · {removing.profile}
          </p>
          <p className="muted">
            Олимпиада исчезнет из навигатора. Напоминания по ней будут отменены.
          </p>
          <div className="dialog-actions">
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => setRemoving(null)}
            >
              Оставить
            </button>
            <button
              className="button danger"
              disabled={busy}
              onClick={() => change(removing.id)}
            >
              Убрать олимпиаду
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
          <p className="data-date">
            Данные актуальны на{" "}
            {(catalog.snapshot_date || "2026-09-30")
              .split("-")
              .reverse()
              .join(".")}
          </p>
          {detail.registry_level && (
            <div className="registry-detail">
              <strong>
                РСОШ · {detail.registry_level} уровень ·{" "}
                {detail.registry_season}
              </strong>
              <button
                className="text-button"
                onClick={() => openSource(detail.registry_source!.url)}
              >
                Перечень РСОШ <Icon name="external" size={15} />
              </button>
            </div>
          )}
          {detail.kind === "vsosh" && (
            <p className="muted">
              ВсОШ: четыре этапа. Уровни I–III РСОШ к ней не применяются.
            </p>
          )}
          <h3>Условия поступления</h3>
          {!benefits(detail).length && (
            <p className="muted">
              Для выбранных программ условия пока не добавлены.
            </p>
          )}
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
                      : "Нет данных"}
                </span>
              </div>
              <dl>
                <dt>Диплом</dt>
                <dd>{b.result}</dd>
                {b.diploma_grades && b.diploma_grades.length > 0 && (
                  <>
                    <dt>Класс диплома</dt>
                    <dd>{b.diploma_grades.join(", ")} класс</dd>
                  </>
                )}
                {b.diploma_validity_years && (
                  <>
                    <dt>Срок действия</dt>
                    <dd>
                      {b.diploma_validity_years} года после года олимпиады
                    </dd>
                    <dt>Льгота на программу</dt>
                    <dd>
                      По правилам приёма {b.admission_year} года. Условия на год
                      твоего поступления могут измениться.
                    </dd>
                  </>
                )}
                <dt>Подтверждение</dt>
                <dd>{b.confirmation}</dd>
              </dl>
              <p className="muted">{b.explanation}</p>
              {b.validity_source && (
                <button
                  className="text-button"
                  onClick={() => openSource(b.validity_source!.url)}
                >
                  О сроке действия диплома <Icon name="external" size={15} />
                </button>
              )}
              <button
                className="text-button"
                onClick={() => openSource(b.source.url)}
              >
                Источник <Icon name="external" size={15} />
              </button>
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
