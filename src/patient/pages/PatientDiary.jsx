
import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import "../styles/patient.css";

const STORAGE_KEY = "patient_demo_diary";

function getToday() {
  const now = new Date();
  const localDate = new Date(
    now.getTime() - now.getTimezoneOffset() * 60000
  );

  return localDate.toISOString().slice(0, 10);
}

function loadEntries() {
  try {
    const saved = JSON.parse(
      localStorage.getItem(STORAGE_KEY) || "[]"
    );

    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

export default function PatientDiary() {
  const location = useLocation();

  const homePath = location.pathname.startsWith(
    "/patient-preview"
  )
    ? "/patient-preview"
    : "/patient";

  const [date, setDate] = useState(getToday());
  const [mood, setMood] = useState(3);
  const [fatigue, setFatigue] = useState("medium");
  const [comment, setComment] = useState("");
  const [entries, setEntries] = useState(loadEntries);
  const [message, setMessage] = useState("");

  function handleSubmit(event) {
    event.preventDefault();

    const entry = {
      id: crypto.randomUUID(),
      date,
      mood: Number(mood),
      fatigue,
      comment: comment.trim(),
      createdAt: new Date().toISOString(),
    };

    const updated = [entry, ...entries];

    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(updated)
      );

      setEntries(updated);
      setComment("");
      setMessage("Запись успешно сохранена.");
    } catch {
      setMessage("Не удалось сохранить запись.");
    }
  }

  const fatigueNames = {
    low: "Низкая",
    medium: "Умеренная",
    high: "Высокая",
  };

  return (
    <main className="patient-dashboard">
      <Link to={homePath} className="patient-back">
        ← Вернуться в кабинет
      </Link>

      <h1>Дневник самочувствия</h1>

      <p>
        Расскажите, как вы себя чувствуете сегодня.
        Заполняйте дневник в удобном для вас темпе.
      </p>

      <form
        className="diary-form"
        onSubmit={handleSubmit}
      >
        <label htmlFor="diary-date">
          Дата
        </label>

        <input
          id="diary-date"
          type="date"
          value={date}
          max={getToday()}
          onChange={(event) => setDate(event.target.value)}
          required
        />

        <fieldset className="diary-fieldset">
          <legend>
            Как вы себя чувствуете?
          </legend>

          <p>
            1 — очень плохо, 5 — очень хорошо
          </p>

          <div className="diary-mood-options">
            {[1, 2, 3, 4, 5].map((value) => (
              <label
                key={value}
                className={`diary-mood-option ${
                  mood === value ? "selected" : ""
                }`}
              >
                <input
                  type="radio"
                  name="mood"
                  value={value}
                  checked={mood === value}
                  onChange={() => setMood(value)}
                />
                <span>{value}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="diary-fieldset">
          <legend>
            Насколько вы устали?
          </legend>

          <div className="diary-fatigue-options">
            {[
              { value: "low", label: "Немного" },
              { value: "medium", label: "Умеренно" },
              { value: "high", label: "Сильно" },
            ].map((option) => (
              <label key={option.value}>
                <input
                  type="radio"
                  name="fatigue"
                  value={option.value}
                  checked={fatigue === option.value}
                  onChange={() => setFatigue(option.value)}
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>

        <label htmlFor="diary-comment">
          Комментарий (необязательно)
        </label>

        <textarea
          id="diary-comment"
          rows="5"
          maxLength={1000}
          value={comment}
          onChange={(event) =>
            setComment(event.target.value)
          }
          placeholder="Например: сегодня упражнения дались легче..."
        />

        <button
          type="submit"
          className="patient-button"
        >
          Сохранить запись
        </button>

        {message && (
          <p role="status">{message}</p>
        )}
      </form>

      <section className="diary-history">
        <h2>История записей</h2>

        {entries.length === 0 ? (
          <p>Пока записей нет.</p>
        ) : (
          <div className="diary-entries">
            {entries.map((entry) => (
              <article
                key={entry.id}
                className="diary-entry"
              >
                <h3>
                  {new Date(
                    `${entry.date}T12:00:00`
                  ).toLocaleDateString("ru-RU")}
                </h3>

                <p>
                  <strong>Самочувствие:</strong>{" "}
                  {entry.mood} из 5
                </p>

                <p>
                  <strong>Усталость:</strong>{" "}
                  {fatigueNames[entry.fatigue]}
                </p>

                {entry.comment && (
                  <p>
                    <strong>Комментарий:</strong>{" "}
                    {entry.comment}
                  </p>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
