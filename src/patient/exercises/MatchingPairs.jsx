
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { saveExerciseResult } from "../utils/exerciseResults.js";
import "../styles/patient.css";

const pictures = [
  { id: 1, symbol: "🍎", name: "Яблоко" },
  { id: 2, symbol: "🌸", name: "Цветок" },
  { id: 3, symbol: "🐱", name: "Кошка" },
  { id: 4, symbol: "⭐", name: "Звезда" },
  { id: 5, symbol: "☀️", name: "Солнце" },
  { id: 6, symbol: "🚗", name: "Машина" },
  { id: 7, symbol: "🏠", name: "Дом" },
  { id: 8, symbol: "🌳", name: "Дерево" },
];

const levels = {
  1: 3,
  2: 6,
  3: 8,
};

function createCards(level) {
  const selected = pictures.slice(0, levels[level]);

  const cards = selected.flatMap((picture) => [
    {
      ...picture,
      cardId: `${picture.id}-a`,
    },
    {
      ...picture,
      cardId: `${picture.id}-b`,
    },
  ]);

  // Перемешиваем карточки
  for (let i = cards.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));

    [cards[i], cards[j]] = [cards[j], cards[i]];
  }

  return cards;
}

export default function MatchingPairs() {
  const location = useLocation();

  const homePath = location.pathname.startsWith(
    "/patient-preview"
  )
    ? "/patient-preview"
    : "/patient";

  const [level, setLevel] = useState(1);
  const [cards, setCards] = useState(() => createCards(1));
  const [opened, setOpened] = useState([]);
  const [matched, setMatched] = useState([]);
  const [moves, setMoves] = useState(0);
  const [errors, setErrors] = useState(0);
  const [locked, setLocked] = useState(false);
  const [saved, setSaved] = useState(null);

  const startTimeRef = useRef(null);
  const resultSavedRef = useRef(false);
  const timerRef = useRef(null);
  const gameIdRef = useRef(0);

  const totalPairs = levels[level];
  const completed = matched.length === totalPairs;

  // Очищаем таймер при закрытии страницы.
  useEffect(() => {
    return () => {
      clearTimeout(timerRef.current);
    };
  }, []);

  // Обрабатываем совпадение двух открытых карточек.
  useEffect(() => {
    if (opened.length !== 2) return;

    const first = cards.find(
      (card) => card.cardId === opened[0]
    );

    const second = cards.find(
      (card) => card.cardId === opened[1]
    );

    if (!first || !second) return;

    if (first.id === second.id) {
      setMatched((previous) => [
        ...previous,
        first.id,
      ]);

      setOpened([]);
      setLocked(false);
      return;
    }

    // Несовпадение считается одной ошибкой.
    setErrors((previous) => previous + 1);

    const currentGameId = gameIdRef.current;

    timerRef.current = setTimeout(() => {
      if (currentGameId !== gameIdRef.current) return;

      setOpened([]);
      setLocked(false);
      timerRef.current = null;
    }, 1500);

    return () => {
      clearTimeout(timerRef.current);
    };
  }, [opened, cards]);

  // Сохраняем результат после нахождения всех пар.
  useEffect(() => {
    if (!completed || resultSavedRef.current) return;

    resultSavedRef.current = true;

    const durationSec = startTimeRef.current
      ? Math.round(
          (Date.now() - startTimeRef.current) / 1000
        )
      : 0;

    // Минимальное число попыток равно числу пар.
    // Чем больше лишних попыток, тем ниже оценка.
    const score =
      moves > 0
        ? Math.round((totalPairs / moves) * 100)
        : 100;

    try {
      saveExerciseResult({
        exerciseId: 4,
        exerciseType: "memory",
        score,
        durationSec,
        errors,
      });

      setSaved(true);
    } catch (error) {
      console.error(
        "Не удалось сохранить результат:",
        error
      );

      setSaved(false);
    }
  }, [completed, moves, errors, totalPairs]);

  function openCard(card) {
    if (
      locked ||
      completed ||
      opened.includes(card.cardId) ||
      matched.includes(card.id)
    ) {
      return;
    }

    // Начинаем отсчёт времени с первой карточки.
    if (startTimeRef.current === null) {
      startTimeRef.current = Date.now();
    }

    if (opened.length === 0) {
      setOpened([card.cardId]);
      return;
    }

    setLocked(true);

    setOpened((previous) => [
      ...previous,
      card.cardId,
    ]);

    setMoves((previous) => previous + 1);
  }

  function restart(newLevel = level) {
    clearTimeout(timerRef.current);
    timerRef.current = null;
    gameIdRef.current += 1;

    setLevel(newLevel);
    setCards(createCards(newLevel));
    setOpened([]);
    setMatched([]);
    setMoves(0);
    setErrors(0);
    setLocked(false);
    setSaved(null);

    startTimeRef.current = null;
    resultSavedRef.current = false;
  }

  return (
    <main className="patient-dashboard">
      <Link
        to={homePath}
        className="patient-back"
      >
        ← Вернуться к упражнениям
      </Link>

      <h1>Поиск пар</h1>

      <p>
        Открывайте по две карточки и находите
        одинаковые изображения. Если картинки
        совпадают, они останутся открытыми.
        Время на выполнение не ограничено.
      </p>

      <div className="pairs-levels">
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

      <section className="pairs-progress">
        <p aria-live="polite">
          <strong>Найдено пар:</strong>{" "}
          {matched.length} из {totalPairs}
        </p>

        <p>
          <strong>Попыток:</strong> {moves}
        </p>

        <p>
          <strong>Ошибок:</strong> {errors}
        </p>
      </section>

      {completed ? (
        <section className="target-result">
          <h2>Упражнение выполнено!</h2>

          <p>
            Вы нашли все {totalPairs} пар.
          </p>

          <p>
            Количество попыток: {moves}
          </p>

          <p>
            Количество ошибок: {errors}
          </p>

          <p aria-live="polite">
            {saved === true
              ? "Результат сохранён в этом браузере."
              : saved === false
                ? "Не удалось сохранить результат."
                : "Сохранение результата…"}
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
        <div className="pairs-grid">
          {cards.map((card) => {
            const isOpen =
              opened.includes(card.cardId) ||
              matched.includes(card.id);

            return (
              <button
                key={card.cardId}
                type="button"
                className={`pairs-card ${
                  isOpen ? "pairs-card-open" : ""
                } ${
                  matched.includes(card.id)
                    ? "pairs-card-matched"
                    : ""
                }`}
                onClick={() => openCard(card)}
                disabled={
                  locked ||
                  matched.includes(card.id)
                }
                aria-label={
                  isOpen
                    ? card.name
                    : "Закрытая карточка"
                }
                aria-pressed={isOpen}
              >
                {isOpen ? (
                  <span aria-hidden="true">
                    {card.symbol}
                  </span>
                ) : (
                  <span aria-hidden="true">
                    ?
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </main>
  );
}

