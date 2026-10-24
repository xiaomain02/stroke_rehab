
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import "../styles/patient.css";

export default function VideoRecording() {
  const location = useLocation();

  const homePath = location.pathname.startsWith(
    "/patient-preview"
  )
    ? "/patient-preview"
    : "/patient";

  const liveVideoRef = useRef(null);
  const streamRef = useRef(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const videoUrlRef = useRef(null);

  const [cameraOn, setCameraOn] = useState(false);
  const [recording, setRecording] = useState(false);
  const [videoUrl, setVideoUrl] = useState(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState(
    "Камера выключена"
  );

  function stopCamera() {
    if (streamRef.current) {
      streamRef.current
        .getTracks()
        .forEach((track) => track.stop());

      streamRef.current = null;
    }

    if (liveVideoRef.current) {
      liveVideoRef.current.srcObject = null;
    }

    setCameraOn(false);
  }

  function clearVideo() {
    if (videoUrlRef.current) {
      URL.revokeObjectURL(videoUrlRef.current);
      videoUrlRef.current = null;
    }

    setVideoUrl(null);
  }

  async function startCamera() {
    setError("");

    if (!navigator.mediaDevices?.getUserMedia) {
      setError(
        "Ваш браузер не поддерживает доступ к камере."
      );
      return;
    }

    try {
      const stream =
        await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true,
        });

      streamRef.current = stream;

      if (liveVideoRef.current) {
        liveVideoRef.current.srcObject = stream;
      }

      setCameraOn(true);
      setStatus("Камера включена");
    } catch (err) {
      if (err.name === "NotAllowedError") {
        setError(
          "Доступ к камере или микрофону запрещён. " +
          "Разрешите доступ в настройках браузера."
        );
      } else if (err.name === "NotFoundError") {
        setError(
          "Камера или микрофон не найдены."
        );
      } else {
        setError(
          "Не удалось включить камеру: " + err.message
        );
      }
    }
  }

  function startRecording() {
    if (!streamRef.current) return;

    if (!window.MediaRecorder) {
      setError(
        "Ваш браузер не поддерживает запись видео."
      );
      return;
    }

    setError("");
    clearVideo();
    chunksRef.current = [];

    const supportedTypes = [
      "video/webm;codecs=vp9,opus",
      "video/webm;codecs=vp8,opus",
      "video/webm",
      "video/mp4",
    ];

    const mimeType = supportedTypes.find(
      (type) => MediaRecorder.isTypeSupported(type)
    );

    try {
      const recorder = mimeType
        ? new MediaRecorder(streamRef.current, {
            mimeType,
          })
        : new MediaRecorder(streamRef.current);

      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        if (chunksRef.current.length > 0) {
          const blob = new Blob(
            chunksRef.current,
            {
              type:
                recorder.mimeType ||
                "video/webm",
            }
          );

          const url = URL.createObjectURL(blob);

          videoUrlRef.current = url;
          setVideoUrl(url);
          setStatus("Запись завершена");
        }

        setRecording(false);
        stopCamera();
      };

      recorder.onerror = () => {
        setError("Произошла ошибка при записи видео.");
        setRecording(false);
      };

      recorder.start();

      setRecording(true);
      setStatus("Идёт запись");
    } catch (err) {
      setError(
        "Не удалось начать запись: " + err.message
      );
    }
  }

  function stopRecording() {
    const recorder = recorderRef.current;

    if (
      recorder &&
      recorder.state === "recording"
    ) {
      recorder.stop();
      setStatus("Обработка видеозаписи…");
    }
  }

  function turnOffCamera() {
    if (recording) {
      stopRecording();
    } else {
      stopCamera();
      setStatus("Камера выключена");
    }
  }

  useEffect(() => {
    return () => {
      const recorder = recorderRef.current;

      if (recorder && recorder.state !== "inactive") {
        recorder.onstop = null;
        recorder.stop();
      }

      if (streamRef.current) {
        streamRef.current
          .getTracks()
          .forEach((track) => track.stop());
      }

      if (videoUrlRef.current) {
        URL.revokeObjectURL(videoUrlRef.current);
      }
    };
  }, []);

  return (
    <main className="patient-dashboard">
      <Link
        to={homePath}
        className="patient-back"
      >
        ← Вернуться в кабинет
      </Link>

      <h1>Видеозапись упражнения</h1>

      <p>
        Запишите выполнение упражнения,
        назначенного врачом. Перед началом
        убедитесь, что камера расположена удобно.
      </p>

      <section className="patient-video-section">
        <h2>Камера</h2>

        <p>
          <strong>Состояние:</strong> {status}
        </p>

        {error && (
          <p className="patient-video-error" role="alert">
            {error}
          </p>
        )}

        <video
          ref={liveVideoRef}
          autoPlay
          muted
          playsInline
          className="patient-video-preview"
          style={{
            display: cameraOn ? "block" : "none",
          }}
        />

        {!cameraOn && !recording && (
          <div className="patient-video-placeholder">
            Камера выключена
          </div>
        )}

        <div className="patient-video-controls">
          {!cameraOn && !recording && (
            <button
              type="button"
              className="patient-button"
              onClick={startCamera}
            >
              Включить камеру
            </button>
          )}

          {cameraOn && !recording && (
            <button
              type="button"
              className="patient-button"
              onClick={startRecording}
            >
              Начать запись
            </button>
          )}

          {recording && (
            <button
              type="button"
              className="patient-button"
              onClick={stopRecording}
            >
              Остановить запись
            </button>
          )}

          {cameraOn && (
            <button
              type="button"
              className="patient-button patient-video-secondary"
              onClick={turnOffCamera}
            >
              Выключить камеру
            </button>
          )}
        </div>
      </section>

      {videoUrl && (
        <section className="patient-video-section">
          <h2>Записанное видео</h2>

          <video
            src={videoUrl}
            controls
            playsInline
            className="patient-video-preview"
          />

          <p>
            Посмотрите запись перед завершением.
          </p>

          <button
            type="button"
            className="patient-button patient-video-secondary"
            onClick={clearVideo}
          >
            Удалить запись
          </button>

          <p>
            Видео пока не отправляется врачу.
            Отправку подключим после готовности API.
          </p>
        </section>
      )}
    </main>
  );
}
