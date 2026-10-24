
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

import { getExerciseResults } from "../utils/exerciseResults.js";
import "../styles/patient.css";

const DIARY_STORAGE_KEY = "patient_demo_diary";

const exerciseNames = {
  1: "Попадание в цели",
  2: "Повторение слов",
  3: "Запоминание последовательности",
  4: "Поиск пар",
};

function loadDiary() {
  try {
    const data = JSON.parse(
      localStorage.getItem(DIARY_STORAGE_KEY) || "[]"
    );

    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

function formatDate(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Дата неизвестна";
  }

  return date.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatDateTime(value) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Дата неизвестна";
  }

  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function isValidResult(result) {
  return (
    result &&
    Object.hasOwn(exerciseNames, result.exercise_id) &&
    typeof result.score === "number" &&
    Number.isFinite(result.score) &&
    result.score >= 0 &&
    result.score <= 100 &&
    typeof result.created_at === "string" &&
    !Number.isNaN(
      new Date(result.created_at).getTime()
    )
  );
}

export default function PatientProgress() {
  const location = useLocation();

  const homePath = location.pathname.startsWith(
    "/patient-preview"
  )
    ? "/patient-preview"
    : "/patient";

  const [entries, setEntries] = useState(loadDiary);
  const [results, setResults] = useState(
    () => getExerciseResults().filter(isValidResult)
  );

  const [selectedExercise, setSelectedExercise] =
    useState("all");

  useEffect(() => {
    function refreshData() {
      setEntries(loadDiary());

      setResults(
        getExerciseResults().filter(isValidResult)
      );
    }

    refreshData();

    window.addEventListener(
      "patient-results-updated",
      refreshData
    );

    window.addEventListener("storage", refreshData);

    return () => {
      window.removeEventListener(
        "patient-results-updated",
        refreshData
      );

      window.removeEventListener(
        "storage",
        refreshData
      );
    };
  }, []);

  // Данные графика самочувствия.
  const diaryChartData = useMemo(() => {
    return entries
      .filter(
        (entry) =>
          typeof entry.date === "string" &&
          Number.isFinite(Number(entry.mood)) &&
          Number(entry.mood) >= 1 &&
          Number(entry.mood) <= 5
      )
      .sort(
        (a, b) =>
          a.date.localeCompare(b.date) ||
          (a.createdAt || "").localeCompare(
            b.createdAt || ""
          )
      )
      .map((entry) => ({
        date: new Date(
          `${entry.date}T12:00:00`
        ).toLocaleDateString("ru-RU", {
          day: "2-digit",
          month: "2-digit",
        }),
        mood: Number(entry.mood),
      }));
  }, [entries]);

  // Сортируем попытки от старых к новым.
  const sortedResults = useMemo(() => {
    return [...results].sort(
      (a, b) =>
        new Date(a.created_at).getTime() -
        new Date(b.created_at).getTime()
    );
  }, [results]);

  const filteredResults = useMemo(() => {
    if (selectedExercise === "all") {
      return sortedResults;
    }

    return sortedResults.filter(
      (result) =>
        result.exercise_id ===
        Number(selectedExercise)
    );
  }, [sortedResults, selectedExercise]);

  // Каждая точка графика — отдельная попытка.
  const exerciseChartData = useMemo(() => {
    return filteredResults.map((result, index) => ({
      attempt: index + 1,
      score: result.score,
      date: formatDateTime(result.created_at),
      exercise: exerciseNames[result.exercise_id],
    }));
  }, [filteredResults]);

  const totalAttempts = results.length;

  const completedExercises = new Set(
    results
      .filter(
        (result) =>
          result.exercise_id !== 3 ||
          (result.score === 100 && result.errors === 0)
      )
      .map((result) => result.exercise_id)
  ).size;

  const averageScore = totalAttempts
    ? Math.round(
        results.reduce(
          (sum, result) => sum + result.score,
          0
        ) / totalAttempts
      )
    : 0;

  const totalErrors = results.reduce(
    (sum, result) =>
      sum + (
        Number.isFinite(Number(result.errors))
          ? Math.max(0, Number(result.errors))
          : 0
      ),
    0
  );

  return (
    <main className="patient-dashboard">
      <Link
        to={homePath}
        className="patient-back"
      >
        ← Вернуться в кабинет
      </Link>

      <h1>Мой прогресс</h1>

      <p>
        Здесь отображаются результаты упражнений
        и записи о самочувствии.
      </p>

      <section className="patient-chart-section">
        <h2>Статистика упражнений</h2>

        <p>
          <strong>Всего попыток:</strong>{" "}
          {totalAttempts}
        </p>

        <p>
          <strong>Упражнений с завершёнными попытками:</strong>{" "}
          {completedExercises} из 4
        </p>

        <p>
          <strong>Средняя игровая оценка:</strong>{" "}
          {totalAttempts ? `${averageScore}%` : "Нет данных"}
        </p>

        <p>
          <strong>Всего зарегистрированных ошибок:</strong>{" "}
          {totalErrors}
        </p>

        <p>
          Оценки разных упражнений рассчитываются
          по разным правилам, поэтому среднее значение
          носит только демонстрационный характер.
        </p>
      </section>

      <section className="patient-chart-section">
        <h2>Результаты упражнений</h2>

        <label
          htmlFor="exercise-filter"
          style={{
            display: "block",
            marginBottom: 12,
          }}
        >
          Выберите упражнение:
        </label>

        <select
          id="exercise-filter"
          value={selectedExercise}
          onChange={(event) =>
            setSelectedExercise(event.target.value)
          }
          style={{
            padding: "10px 12px",
            borderRadius: 8,
            border: "1px solid #ccc",
            marginBottom: 20,
            maxWidth: "100%",
          }}
        >
          <option value="all">
            Все упражнения
          </option>

          {Object.entries(exerciseNames).map(
            ([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            )
          )}
        </select>

        {exerciseChartData.length === 0 ? (
          <div className="patient-chart-empty">
            <p>
              Пока нет сохранённых результатов
              для выбранного упражнения.
            </p>

            <Link
              to={homePath}
              className="patient-button"
            >
              Перейти к упражнениям
            </Link>
          </div>
        ) : (
          <>
            <p>
              Каждая точка — отдельная попытка.
              По горизонтали указан номер попытки,
              по вертикали — игровая оценка от 0 до 100.
            </p>

            <div className="patient-chart">
              <ResponsiveContainer
                width="100%"
                height="100%"
              >
                <LineChart
                  data={exerciseChartData}
                  margin={{
                    top: 20,
                    right: 25,
                    left: 0,
                    bottom: 20,
                  }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                  />

                  <XAxis
                    dataKey="attempt"
                    allowDecimals={false}
                  />

                  <YAxis
                    domain={[0, 100]}
                    ticks={[0, 25, 50, 75, 100]}
                    allowDecimals={false}
                  />

                  <Tooltip
                    labelFormatter={(label) =>
                      `Попытка №${label}`
                    }
                    formatter={(value) => [
                      `${value}%`,
                      "Игровая оценка",
                    ]}
                    contentStyle={{
                      borderRadius: 8,
                    }}
                  />

                  <Legend />

                  <Line
                    type="linear"
                    dataKey="score"
                    name="Игровая оценка"
                    stroke="#7563b5"
                    strokeWidth={3}
                    dot={{ r: 5 }}
                    activeDot={{ r: 7 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <p>
              Для сравнения результатов во времени
              лучше выбирать одно упражнение:
              показатели разных игр не равнозначны.
            </p>
          </>
        )}
      </section>

      <section className="patient-chart-section">
        <h2>История попыток</h2>

        {filteredResults.length === 0 ? (
          <p>
            История пока пуста.
          </p>
        ) : (
          <div
            style={{
              overflowX: "auto",
              width: "100%",
            }}
          >
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                textAlign: "left",
              }}
            >
              <thead>
                <tr>
                  <th style={{ padding: 10 }}>
                    Дата
                  </th>

                  <th style={{ padding: 10 }}>
                    Упражнение
                  </th>

                  <th style={{ padding: 10 }}>
                    Оценка
                  </th>

                  <th style={{ padding: 10 }}>
                    Ошибки
                  </th>

                  <th style={{ padding: 10 }}>
                    Время
                  </th>
                </tr>
              </thead>

              <tbody>
                {[...filteredResults]
                  .reverse()
                  .map((result, index) => (
                    <tr
                      key={result.id || index}
                      style={{
                        borderTop:
                          "1px solid #e4e0ee",
                      }}
                    >
                      <td style={{ padding: 10 }}>
                        {formatDateTime(
                          result.created_at
                        )}
                      </td>

                      <td style={{ padding: 10 }}>
                        {
                          exerciseNames[
                            result.exercise_id
                          ]
                        }
                      </td>

                      <td style={{ padding: 10 }}>
                        {result.score}%
                      </td>

                      <td style={{ padding: 10 }}>
                        {result.errors ?? 0}
                      </td>

                      <td style={{ padding: 10 }}>
                        {Number(
                          result.duration_sec
                        ) || 0} сек.
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="patient-chart-section">
        <h2>Самочувствие по датам</h2>

        {diaryChartData.length === 0 ? (
          <div className="patient-chart-empty">
            <p>
              Пока недостаточно данных для графика.
            </p>

            <Link
              to={`${homePath}/diary`}
              className="patient-button"
            >
              Заполнить дневник
            </Link>
          </div>
        ) : (
          <>
            <p>
              Шкала от 1 до 5, где 1 — очень плохо,
              а 5 — очень хорошо.
            </p>

            <div className="patient-chart">
              <ResponsiveContainer
                width="100%"
                height="100%"
              >
                <LineChart
                  data={diaryChartData}
                  margin={{
                    top: 20,
                    right: 25,
                    left: 0,
                    bottom: 20,
                  }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                  />

                  <XAxis dataKey="date" />

                  <YAxis
                    domain={[1, 5]}
                    ticks={[1, 2, 3, 4, 5]}
                    allowDecimals={false}
                  />

                  <Tooltip />

                  <Line
                    type="linear"
                    dataKey="mood"
                    name="Самочувствие"
                    stroke="#7563b5"
                    strokeWidth={3}
                    dot={{ r: 6 }}
                    activeDot={{ r: 8 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </section>

      <section className="patient-chart-section">
        <h2>Статистика дневника</h2>

        <p>
          <strong>Всего записей:</strong>{" "}
          {entries.length}
        </p>

        <p>
          <strong>Записей на графике:</strong>{" "}
          {diaryChartData.length}
        </p>

        <p>
          Результаты сохраняются локально
          в браузере и пока не передаются врачу.
          Эти показатели не являются медицинской
          оценкой эффективности реабилитации.
        </p>
      </section>
    </main>
  );
}
