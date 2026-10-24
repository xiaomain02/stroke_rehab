
import { useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { saveExerciseResult } from "../utils/exerciseResults.js";
import "../styles/patient.css";

const levels = {
  1: { size: 100, count: 5 },
  2: { size: 75, count: 8 },
  3: { size: 55, count: 10 },
};

export default function MovingTargets() {
  const location = useLocation();

  const isPreview = location.pathname.startsWith(
    "/patient-preview"
  );

  const homePath = isPreview
    ? "/patient-preview"
    : "/patient";

  const [level, setLevel] = useState(1);
  const [hits, setHits] = useState(0);
  const [position, setPosition] = useState({
    x: 50,
    y: 50,
  });
  const [finished, setFinished] = useState(false);
  const [saved, setSaved] = useState(false);

  // Время начала отсчитываем с первого попадания.
  const startTimeRef = useRef(null);
  const completedRef = useRef(false);

  const settings = levels[level];

  function moveTarget() {
    setPosition({
      x: 20 + Math.random() * 60,
      y: 20 + Math.random() * 60,
    });
  }

  function saveResult(finalHits) {
    const durationSec = startTimeRef.current
      ? Math.round(
          (Date.now() - startTimeRef.current) / 1000
        )
      : 0;

    try {
      saveExerciseResult({
        exerciseId: 1,
        exerciseType: "motor",
        score: Math.round(
          (finalHits / settings.count) * 100
        ),
        durationSec,
        errors: 0,
      });

      setSaved(true);
    } catch (error) {
      console.error(
        "Не удалось сохранить результат",
        error
      );
      setSaved(false);
    }
  }

  function handleHit() {
    if (finished || completedRef.current) return;

    if (startTimeRef.current === null) {
      startTimeRef.current = Date.now();
    }

    const nextHits = hits + 1;
    setHits(nextHits);

    if (nextHits >= settings.count) {
      completedRef.current = true;
      setFinished(true);
      saveResult(nextHits);
    } else {
      moveTarget();
    }
  }

  function restart(newLevel = level) {
    setLevel(newLevel);
    setHits(0);
    setFinished(false);
    setSaved(false);
    setPosition({ x: 50, y: 50 });

    startTimeRef.current = null;
    completedRef.current = false;
  }

  return (
    <main className="patient-dashboard">
      <Link
        to={homePath}
        className="patient-back"
      >
        ← Вернуться к упражнениям
      </Link>

      <h1>Попадание в цели</h1>

      <p>
        Нажимайте на круги. Выполняйте упражнение
        спокойно, без ограничения по времени.
      </p>

      <div className="target-levels">
        {[1, 2, 3].map((item) => (
          <button
            key={item}
            type="button"
            className="patient-button"
            onClick={() => restart(item)}
            aria-pressed={level === item}
          >
            Уровень {item}
          </button>
        ))}
      </div>

      <p aria-live="polite">
        Попаданий: {hits} из {settings.count}
      </p>

      {finished ? (
        <section className="target-result">
          <h2>Упражнение выполнено!</h2>

          <p>
            Вы попали во все {settings.count} целей.
          </p>

          <p aria-live="polite">
            {saved
              ? "Результат сохранён в этом браузере."
              : "Результат не удалось сохранить."}
          </p>

          <button
            type="button"
            className="patient-button"
            onClick={() => restart()}
          >
            Повторить упражнение
          </button>

          <Link
            to={homePath}
            className="patient-button"
          >
            Вернуться в кабинет
          </Link>
        </section>
      ) : (
        <div className="target-area">
          <button
            type="button"
            className="target-circle"
            style={{
              width: settings.size,
              height: settings.size,
              left: `${position.x}%`,
              top: `${position.y}%`,
            }}
            onClick={handleHit}
            aria-label="Нажать на цель"
          />
        </div>
      )}
    </main>
  );
}
