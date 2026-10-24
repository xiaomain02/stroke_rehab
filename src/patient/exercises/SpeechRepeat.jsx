
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { saveExerciseResult } from "../utils/exerciseResults.js";
import "../styles/patient.css";

const tasks = {
  1: [
    "Мама",
    "Дом",
    "Солнце",
    "Книга",
  ],
  2: [
    "Доброе утро",
    "Сегодня хорошая погода",
    "Я читаю книгу",
  ],
  3: [
    "Сегодня я выполняю упражнения для речи.",
    "После завтрака я решил почитать книгу.",
    "Мне нравится проводить время с семьёй.",
  ],
};

export default function SpeechRepeat() {
  const location = useLocation();

  const homePath = location.pathname.startsWith(
    "/patient-preview"
  )
    ? "/patient-preview"
    : "/patient";

  const [level, setLevel] = useState(1);
  const [taskIndex, setTaskIndex] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [error, setError] = useState("");
  const [completed, setCompleted] = useState(false);
  const [saved, setSaved] = useState(false);

  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const audioUrlRef = useRef(null);

  const startTimeRef = useRef(null);
  const completedRef = useRef(false);
  const mountedRef = useRef(true);
  const recordingSessionRef = useRef(0);

  const currentTask = tasks[level][taskIndex];

  function clearAudio() {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }

    setAudioUrl(null);
  }

  function stopTracks() {
    streamRef.current?.getTracks().forEach(
      (track) => track.stop()
    );

    streamRef.current = null;
  }

  function stopRecording() {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
    }
  }

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
      recordingSessionRef.current += 1;

      const recorder = recorderRef.current;

      if (recorder && recorder.state !== "inactive") {
        recorder.onstop = null;
        recorder.stop();
      }

      stopTracks();

      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = null;
      }
    };
  }, []);

  async function startRecording() {
    setError("");

    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === "undefined"
    ) {
      setError(
        "Ваш браузер не поддерживает запись звука."
      );
      return;
    }

    clearAudio();

    const session = ++recordingSessionRef.current;

    try {
      const stream =
        await navigator.mediaDevices.getUserMedia({
          audio: true,
        });

      if (
        !mountedRef.current ||
        session !== recordingSessionRef.current
      ) {
        stream.getTracks().forEach(
          (track) => track.stop()
        );
        return;
      }

      streamRef.current = stream;
      chunksRef.current = [];

      const recorder = new MediaRecorder(stream);

      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });

        if (
          mountedRef.current &&
          session === recordingSessionRef.current &&
          blob.size > 0
        ) {
          const url = URL.createObjectURL(blob);

          audioUrlRef.current = url;
          setAudioUrl(url);
        }

        if (mountedRef.current) {
          setIsRecording(false);
        }

        stopTracks();
      };

      recorder.onerror = () => {
        if (mountedRef.current) {
          setError(
            "Произошла ошибка при записи звука."
          );
          setIsRecording(false);
        }

        stopTracks();
      };

      recorder.start();

      if (startTimeRef.current === null) {
        startTimeRef.current = Date.now();
      }

      setIsRecording(true);
    } catch {
      if (mountedRef.current) {
        setError(
          "Не удалось включить микрофон. Проверьте разрешение браузера."
        );
      }

      stopTracks();
    }
  }

  function changeLevel(newLevel) {
    if (isRecording) return;

    recordingSessionRef.current += 1;
    clearAudio();

    setLevel(newLevel);
    setTaskIndex(0);
    setCompleted(false);
    setSaved(false);
    setError("");

    startTimeRef.current = null;
    completedRef.current = false;
  }

  function saveResult() {
    const durationSec = startTimeRef.current
      ? Math.round(
          (Date.now() - startTimeRef.current) / 1000
        )
      : 0;

    try {
      saveExerciseResult({
        exerciseId: 2,
        exerciseType: "speech",
        score: 100,
        durationSec,
        errors: 0,
      });

      setSaved(true);
    } catch (err) {
      console.error(
        "Не удалось сохранить результат:",
        err
      );

      setSaved(false);
    }
  }

  function nextTask() {
    if (isRecording || !audioUrl) return;

    clearAudio();

    if (taskIndex + 1 < tasks[level].length) {
      setTaskIndex((index) => index + 1);
    } else if (!completedRef.current) {
      completedRef.current = true;
      setCompleted(true);
      saveResult();
    }
  }

  function restart() {
    changeLevel(level);
  }

  return (
    <main className="patient-dashboard">
      <Link
        to={homePath}
        className="patient-back"
      >
        ← Вернуться к упражнениям
      </Link>

      <h1>Повторение слов</h1>

      <p>
        Прочитайте слово или фразу вслух.
        Запишите свой голос и прослушайте запись.
        Не торопитесь.
      </p>

      <div className="speech-levels">
        {[1, 2, 3].map((item) => (
          <button
            key={item}
            type="button"
            className="patient-button"
            onClick={() => changeLevel(item)}
            disabled={isRecording}
            aria-pressed={level === item}
          >
            Уровень {item}
          </button>
        ))}
      </div>

      {completed ? (
        <section className="target-result">
          <h2>Упражнение завершено!</h2>

          <p>
            Вы прошли все задания уровня {level}.
          </p>

          <p aria-live="polite">
            {saved
              ? "Результат сохранён в этом браузере."
              : "Не удалось сохранить результат."}
          </p>

          <p>
            Записи пока не отправлены врачу.
            Сохранён только факт завершения заданий.
          </p>

          <button
            type="button"
            className="patient-button"
            onClick={restart}
          >
            Повторить
          </button>

          <Link
            to={homePath}
            className="patient-button"
          >
            Вернуться в кабинет
          </Link>
        </section>
      ) : (
        <section className="speech-task">
          <p>
            Задание {taskIndex + 1} из{" "}
            {tasks[level].length}
          </p>

          <h2 className="speech-word">
            {currentTask}
          </h2>

          <div className="speech-controls">
            {!isRecording ? (
              <button
                type="button"
                className="patient-button"
                onClick={startRecording}
              >
                🎤 Начать запись
              </button>
            ) : (
              <button
                type="button"
                className="patient-button"
                onClick={stopRecording}
              >
                ⏹ Остановить запись
              </button>
            )}
          </div>

          {isRecording && (
            <p role="status">
              Идёт запись. Произнесите фразу
              и нажмите «Остановить запись».
            </p>
          )}

          {error && (
            <p
              role="alert"
              className="speech-error"
            >
              {error}
            </p>
          )}

          {audioUrl && !isRecording && (
            <div className="speech-playback">
              <h3>Ваша запись</h3>

              <audio
                controls
                src={audioUrl}
                aria-label="Прослушать запись"
              />

              <p>
                Если хотите, можете записать
                ответ ещё раз.
              </p>

              <button
                type="button"
                className="patient-button"
                onClick={nextTask}
              >
                {taskIndex + 1 === tasks[level].length
                  ? "Завершить упражнение"
                  : "Следующее задание"}
              </button>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
