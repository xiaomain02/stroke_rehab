
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { saveExerciseResult } from "../utils/exerciseResults.js";
import "../styles/patient.css";

const colors = [
  { id: 0, name: "Красный", color: "#e88b94" },
  { id: 1, name: "Синий", color: "#88aee8" },
  { id: 2, name: "Зелёный", color: "#8bc9a3" },
  { id: 3, name: "Жёлтый", color: "#e8ca79" },
];

const levels = {
  1: 3,
  2: 4,
  3: 5,
};

export default function MemorySequence() {
  const location = useLocation();

  const homePath = location.pathname.startsWith(
    "/patient-preview"
  )
    ? "/patient-preview"
    : "/patient";

  const [level, setLevel] = useState(1);
  const [sequence, setSequence] = useState([]);
  const [activeColor, setActiveColor] = useState(null);
  const [userInput, setUserInput] = useState([]);
  const [phase, setPhase] = useState("ready");
  const [saved, setSaved] = useState(null);

  const [message, setMessage] = useState(
    "Нажмите «Показать последовательность», чтобы начать."
  );

  const timersRef = useRef([]);
  const sequenceRef = useRef([]);
  const phaseRef = useRef("ready");
  const startTimeRef = useRef(null);
  const resultSavedRef = useRef(false);

  function clearTimers() {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }

  function updatePhase(nextPhase) {
    phaseRef.current = nextPhase;
    setPhase(nextPhase);
  }

  useEffect(() => {
    return () => {
      timersRef.current.forEach(clearTimeout);
    };
  }, []);

  function reset(newLevel = level) {
    clearTimers();

    setLevel(newLevel);
    setSequence([]);
    sequenceRef.current = [];
    setUserInput([]);
    setActiveColor(null);
    setSaved(null);

    startTimeRef.current = null;
    resultSavedRef.current = false;

    updatePhase("ready");

    setMessage(
      "Нажмите «Показать последовательность», чтобы начать."
    );
  }

  function startGame() {
    clearTimers();

    const newSequence = Array.from(
      { length: levels[level] },
      () => Math.floor(Math.random() * colors.length)
    );

    sequenceRef.current = newSequence;

    setSequence(newSequence);
    setUserInput([]);
    setActiveColor(null);
    setSaved(null);

    startTimeRef.current = Date.now();
    resultSavedRef.current = false;

    updatePhase("showing");
    setMessage("Запоминайте порядок цветов.");

    newSequence.forEach((colorId, index) => {
      const startTimer = setTimeout(() => {
        setActiveColor(colorId);
      }, 700 + index * 1300);

      const endTimer = setTimeout(() => {
        setActiveColor(null);
      }, 1500 + index * 1300);

      timersRef.current.push(startTimer, endTimer);
    });

    const finishTimer = setTimeout(() => {
      setActiveColor(null);
      updatePhase("input");
      setMessage("Теперь повторите последовательность.");
    }, 700 + newSequence.length * 1300);

    timersRef.current.push(finishTimer);
  }

  function saveResult(correctCount, hasError) {
    if (resultSavedRef.current) return;

    resultSavedRef.current = true;

    const durationSec = startTimeRef.current
      ? Math.round(
          (Date.now() - startTimeRef.current) / 1000
        )
      : 0;

    const score = Math.round(
      (correctCount / sequenceRef.current.length) * 100
    );

    try {
      saveExerciseResult({
        exerciseId: 3,
        exerciseType: "memory",
        score,
        durationSec,
        errors: hasError ? 1 : 0,
      });

      setSaved(true);
    } catch (error) {
      console.error(
        "Не удалось сохранить результат:",
        error
      );

      setSaved(false);
    }
  }

  function handleColorClick(colorId) {
    if (phaseRef.current !== "input") return;

    const nextInput = [...userInput, colorId];
    setUserInput(nextInput);

    const expected =
      sequenceRef.current[nextInput.length - 1];

    if (colorId !== expected) {
      updatePhase("incorrect");

      setMessage(
        "Последовательность не совпала. Можно попробовать ещё раз."
      );

      // Текущий неправильный выбор не учитываем
      // как правильно воспроизведённый цвет.
      saveResult(nextInput.length - 1, true);
      return;
    }

    if (
      nextInput.length === sequenceRef.current.length
    ) {
      updatePhase("completed");

      setMessage(
        "Отлично! Последовательность повторена."
      );

      saveResult(nextInput.length, false);
    }
  }

  return (
    <main className="patient-dashboard">
      <Link
        to={homePath}
        className="patient-back"
      >
        ← Вернуться к упражнениям
      </Link>

      <h1>Запоминание последовательности</h1>

      <p>
        Посмотрите, в каком порядке подсвечиваются
        цветные кнопки, затем повторите этот порядок.
        Время на ответ не ограничено.
      </p>

      <div className="memory-levels">
        {[1, 2, 3].map((item) => (
          <button
            key={item}
            type="button"
            className="patient-button"
            onClick={() => reset(item)}
            aria-pressed={level === item}
          >
            Уровень {item}
          </button>
        ))}
      </div>

      <p>
        <strong>Длина последовательности:</strong>{" "}
        {levels[level]}
      </p>

      <section className="memory-game">
        <p
          role="status"
          className="memory-message"
        >
          {message}
        </p>

        <div className="memory-grid">
          {colors.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`memory-color ${
                activeColor === item.id
                  ? "memory-color-active"
                  : ""
              }`}
              style={{
                backgroundColor: item.color,
              }}
              onClick={() =>
                handleColorClick(item.id)
              }
              disabled={phase !== "input"}
              aria-label={item.name}
            >
              {item.name}
            </button>
          ))}
        </div>

        {phase === "input" && (
          <p>
            Вы выбрали: {userInput.length} из{" "}
            {sequence.length}
          </p>
        )}

        {phase === "ready" && (
          <button
            type="button"
            className="patient-button"
            onClick={startGame}
          >
            Показать последовательность
          </button>
        )}

        {(phase === "incorrect" ||
          phase === "completed") && (
          <div className="memory-result">
            {saved === true && (
              <p aria-live="polite">
                Результат сохранён в этом браузере.
              </p>
            )}

            {saved === false && (
              <p role="alert">
                Не удалось сохранить результат.
              </p>
            )}

            <button
              type="button"
              className="patient-button"
              onClick={startGame}
            >
              Новая последовательность
            </button>

            <button
              type="button"
              className="patient-button"
              onClick={() => reset()}
            >
              Начать заново
            </button>
          </div>
        )}
      </section>
    </main>
  );
}
