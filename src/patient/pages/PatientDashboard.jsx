
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../../api.js";
import {
  getExerciseResults,
  getExerciseStats,
} from "../utils/exerciseResults.js";
import "../styles/patient.css";

const exerciseConfig = {
  1: {
    path: "targets",
    category: "Моторика",
    description: "Нажимайте на появляющиеся цели.",
  },
  2: {
    path: "speech",
    category: "Речь",
    description: "Произнесите предложенные слова вслух.",
  },
  3: {
    path: "memory",
    category: "Память",
    description: "Запомните и повторите последовательность.",
  },
  4: {
    path: "pairs",
    category: "Память",
    description: "Найдите одинаковые картинки.",
  },
};

const videoExercise = {
  id: "video-demo",
  title: "Видеозапись движения",
  category: "Моторика",
  level: 1,
  description: "Запишите выполнение упражнения на камеру.",
  path: "video",
  demo: true,
};

const EMPTY_STATS = {
  total: 0,
  averageScore: 0,
  completedExercises: 0,
};

export default function PatientDashboard() {
  const location = useLocation();

  const basePath = location.pathname.startsWith(
    "/patient-preview"
  )
    ? "/patient-preview"
    : "/patient";

  const [exercises, setExercises] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState(EMPTY_STATS);

  useEffect(() => {
    let cancelled = false;

    async function loadExercises() {
      setLoading(true);
      setError("");

      try {
        const data = await api.exercises();

        if (!Array.isArray(data)) {
          throw new Error(
            "Сервер вернул неверный формат упражнений."
          );
        }

        const prepared = data.map((exercise) => {
          const config = exerciseConfig[exercise.id];

          return {
            ...exercise,
            title: exercise.title || "Упражнение",
            category:
              config?.category ||
              exercise.type ||
              "Упражнение",
            description:
              config?.description ||
              "Выполните упражнение по инструкции.",
            path: config?.path || null,
            level: exercise.level ?? null,
          };
        });

        if (!cancelled) {
          setExercises(prepared);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err.message ||
              "Не удалось загрузить упражнения."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadExercises();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function updateResults() {
      const savedResults = getExerciseResults();

      // Учитываем только записи нового формата.
      const validResults = savedResults.filter(
        (result) =>
          Number.isInteger(result.exercise_id) &&
          typeof result.score === "number" &&
          Number.isFinite(result.score) &&
          typeof result.created_at === "string"
      );

      setResults(validResults);
      setStats(getExerciseStats());
    }

    updateResults();

    window.addEventListener(
      "patient-results-updated",
      updateResults
    );

    window.addEventListener("storage", updateResults);

    return () => {
      window.removeEventListener(
        "patient-results-updated",
        updateResults
      );
      window.removeEventListener(
        "storage",
        updateResults
      );
    };
  }, []);

  const completedIds = new Set(
    results
      .filter(
        (result) =>
          result.exercise_id !== 3 ||
          (result.score === 100 && result.errors === 0)
      )
      .map((result) => result.exercise_id)
  );

  const completedCount = exercises.filter(
    (exercise) => completedIds.has(Number(exercise.id))
  ).length;

  const progressPercent = exercises.length
    ? Math.round(
        (completedCount / exercises.length) * 100
      )
    : 0;

  const displayedExercises = [
    ...exercises,
    videoExercise,
  ];

  return (
    <main className="patient-dashboard">
      <header className="patient-header">
        <h1>Личный кабинет пациента</h1>

        <p>
          Здесь находятся ваши упражнения,
          дневник самочувствия и прогресс.
        </p>
      </header>

      <section className="patient-progress">
        <h2>Мой прогресс</h2>

        <p>
          <strong>Выполнено упражнений:</strong>{" "}
          {completedCount} из {exercises.length}
        </p>

        <progress
          value={completedCount}
          max={exercises.length || 1}
          aria-label="Прогресс выполнения упражнений"
        />

        <p>{progressPercent}% выполнено</p>

        <p>
          <strong>Всего сохранённых попыток:</strong>{" "}
          {stats.total}
        </p>

        <p>
          <strong>Средняя игровая оценка:</strong>{" "}
          {stats.averageScore}%
        </p>

        <p>
          Это демонстрационные результаты,
          сохранённые только в данном браузере.
          Они не являются медицинской оценкой.
        </p>
      </section>

      <section className="patient-exercises">
        <h2>Мои упражнения</h2>

        {loading && (
          <p role="status">Загружаем упражнения…</p>
        )}

        {error && (
          <p role="alert" style={{ color: "#a52828" }}>
            {error}
          </p>
        )}

        {!loading && !error && exercises.length === 0 && (
          <p>В API пока нет доступных упражнений.</p>
        )}

        {!loading && (
          <div className="patient-exercises-grid">
            {displayedExercises.map((exercise) => {
              const isCompleted = completedIds.has(
                Number(exercise.id)
              );

              const status = exercise.demo
                ? "Демонстрация"
                : isCompleted
                  ? "Выполнено"
                  : "Не выполнено";

              return (
                <article
                  key={exercise.id}
                  className="patient-exercise-card"
                >
                  <span className="patient-category">
                    {exercise.category}
                  </span>

                  <h3>{exercise.title}</h3>

                  <p>{exercise.description}</p>

                  {exercise.level !== null && (
                    <p>
                      <strong>Уровень:</strong>{" "}
                      {exercise.level}
                    </p>
                  )}

                  <p>
                    <strong>Статус:</strong>{" "}
                    <span
                      className={`patient-status ${
                        isCompleted
                          ? "status-done"
                          : "status-new"
                      }`}
                    >
                      {status}
                    </span>
                  </p>

                  {exercise.path ? (
                    <Link
                      to={`${basePath}/${exercise.path}`}
                      className="patient-button"
                    >
                      {exercise.demo
                        ? "Открыть видеозапись"
                        : isCompleted
                          ? "Пройти ещё раз"
                          : "Начать упражнение"}
                    </Link>
                  ) : (
                    <p>
                      Для этого упражнения пока
                      не подключён интерактивный компонент.
                    </p>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section className="patient-menu">
        <h2>Дополнительно</h2>

        <Link
          to={`${basePath}/diary`}
          className="patient-button"
        >
          Дневник самочувствия
        </Link>

        <Link
          to={`${basePath}/progress`}
          className="patient-button"
        >
          График прогресса
        </Link>
      </section>
    </main>
  );
}
