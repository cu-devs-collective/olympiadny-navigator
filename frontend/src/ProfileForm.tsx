import { useState } from "react";
import type { FormEvent } from "react";
import type { Catalog, Profile } from "./route-api";
import { Icon } from "./icons";

function graduationYear(grade: number) {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: "Europe/Moscow",
    year: "numeric",
    month: "numeric",
  }).formatToParts(new Date());
  return (
    Number(parts.find((p) => p.type === "year")!.value) +
    (Number(parts.find((p) => p.type === "month")!.value) >= 9 ? 1 : 0) +
    11 -
    grade
  );
}
function detectTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Moscow";
  } catch {
    return "Europe/Moscow";
  }
}
export function ProfileForm({
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
    timezone: initial.program_ids.length ? initial.timezone : detectTimezone(),
  });
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("");
  const [university, setUniversity] = useState("");
  const [direction, setDirection] = useState("");
  const [subjectQuery, setSubjectQuery] = useState("");
  const [page, setPage] = useState(0);
  const options = (field: "campus" | "university" | "direction") =>
    [
      ...new Set(
        catalog.programs
          .map((p) => p[field])
          .filter((v): v is string => Boolean(v)),
      ),
    ].sort();
  const programs = catalog.programs.filter(
    (program) =>
      (!city || program.campus === city) &&
      (!university || program.university === university) &&
      (!direction || program.direction === direction) &&
      `${program.name} ${program.short_name} ${program.university} ${program.direction}`
        .toLocaleLowerCase("ru")
        .includes(query.toLocaleLowerCase("ru")),
  );
  const pages = Math.max(1, Math.ceil(programs.length / 12)),
    current = Math.min(page, pages - 1);
  const selected = catalog.programs.filter((program) =>
    p.program_ids.includes(program.id),
  );
  function toggleProgram(id: string) {
    setP({
      ...p,
      program_ids: p.program_ids.includes(id)
        ? p.program_ids.filter((v) => v !== id)
        : [...p.program_ids, id],
    });
  }
  function toggleSubject(id: Profile["subjects"][number]) {
    setP({
      ...p,
      subjects: p.subjects.includes(id)
        ? p.subjects.filter((v) => v !== id)
        : [...p.subjects, id],
    });
  }
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
        </label>
      </div>
      <fieldset>
        <legend>Куда хочешь поступить?</legend>
        <p className="muted">Выбрано {p.program_ids.length} из 2 программ</p>
        {selected.length > 0 && (
          <div className="selected-programs" aria-label="Выбранные программы">
            {selected.map((program) => (
              <button
                type="button"
                key={program.id}
                className="selection-chip"
                onClick={() => toggleProgram(program.id)}
                aria-label={`Убрать цель: ${program.name}`}
              >
                {program.university} · {program.short_name}
                <Icon name="close" size={14} />
              </button>
            ))}
          </div>
        )}
        <label className="program-search">
          Поиск программы
          <input
            type="search"
            placeholder="Название, код или вуз"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(0);
            }}
          />
        </label>
        <div className="program-filters">
          <label>
            Город
            <select
              aria-label="Город"
              value={city}
              onChange={(e) => {
                setCity(e.target.value);
                setPage(0);
              }}
            >
              <option value="">Все города</option>
              {options("campus").map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <label>
            Вуз
            <select
              aria-label="Вуз"
              value={university}
              onChange={(e) => {
                setUniversity(e.target.value);
                setPage(0);
              }}
            >
              <option value="">Все вузы</option>
              {options("university").map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <label className="direction-filter">
            Направление
            <select
              aria-label="Направление"
              value={direction}
              onChange={(e) => {
                setDirection(e.target.value);
                setPage(0);
              }}
            >
              <option value="">Все направления</option>
              {options("direction").map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="program-result-line">
          <small>Найдено программ: {programs.length}</small>
          {(query || city || university || direction) && (
            <button
              type="button"
              className="text-button"
              onClick={() => {
                setQuery("");
                setCity("");
                setUniversity("");
                setDirection("");
                setPage(0);
              }}
            >
              Сбросить
            </button>
          )}
        </div>
        <div className="program-options" aria-label="Программы вузов">
          {programs.slice(current * 12, current * 12 + 12).map((program) => (
            <label
              key={program.id}
              className={`program-option ${p.program_ids.includes(program.id) ? "selected" : ""}`}
            >
              <input
                type="checkbox"
                aria-label={`${program.university}, ${program.name}`}
                checked={p.program_ids.includes(program.id)}
                disabled={
                  !p.program_ids.includes(program.id) &&
                  p.program_ids.length >= 2
                }
                onChange={() => toggleProgram(program.id)}
              />
              <span>
                <small>
                  {program.university} · {program.campus}
                </small>
                <strong>{program.name}</strong>
                <small>{program.direction}</small>
              </span>
            </label>
          ))}
          {!programs.length && (
            <p className="program-empty">
              Нет программ с такими условиями. Попробуй изменить фильтры.
            </p>
          )}
        </div>
        {pages > 1 && (
          <div className="pagination">
            <button
              type="button"
              className="button secondary"
              disabled={current === 0}
              onClick={() => setPage(current - 1)}
            >
              Назад
            </button>
            <small>
              {current + 1} / {pages}
            </small>
            <button
              type="button"
              className="button secondary"
              disabled={current === pages - 1}
              onClick={() => setPage(current + 1)}
            >
              Далее
            </button>
          </div>
        )}
      </fieldset>
      <fieldset>
        <legend>Интересующие предметы</legend>
        <div className="selected-subjects">
          {catalog.subjects
            .filter((s) => p.subjects.includes(s.id))
            .map((s) => (
              <button
                type="button"
                className="selection-chip"
                key={s.id}
                onClick={() => toggleSubject(s.id)}
                aria-label={`Убрать предмет: ${s.name}`}
              >
                {s.name}
                <Icon name="close" size={14} />
              </button>
            ))}
        </div>
        <details className="subject-picker">
          <summary>
            Выбрать предметы <span>{p.subjects.length} выбрано</span>
          </summary>
          <input
            type="search"
            aria-label="Поиск предметов"
            placeholder="Найти предмет"
            value={subjectQuery}
            onChange={(e) => setSubjectQuery(e.target.value)}
          />
          <div className="subject-options">
            {catalog.subjects
              .filter((s) =>
                s.name
                  .toLocaleLowerCase("ru")
                  .includes(subjectQuery.toLocaleLowerCase("ru")),
              )
              .map((s) => (
                <label key={s.id}>
                  <input
                    type="checkbox"
                    checked={p.subjects.includes(s.id)}
                    onChange={() => toggleSubject(s.id)}
                  />
                  {s.name}
                </label>
              ))}
          </div>
        </details>
      </fieldset>
      <button
        className="button primary"
        disabled={
          busy || !p.consent || !p.program_ids.length || !p.subjects.length
        }
      >
        {busy ? "Сохраняем…" : "Сохранить"}
      </button>
    </form>
  );
}
