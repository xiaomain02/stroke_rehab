import { useEffect, useState } from 'react'
import { api } from '../api.js'

const TYPES = { motor: 'Моторика', speech: 'Речь', memory: 'Память' }

export default function Exercises() {
  const [list, setList] = useState(null)
  const [msg, setMsg] = useState(null)
  const [busyId, setBusyId] = useState(null)
  const load = () => api.exercises().then(setList).catch((e) => setMsg({ text: e.message, err: true }))
  useEffect(() => { load() }, [])

  async function upload(id, file) {
    if (!file) return
    if (file.size > 200 * 1024 * 1024) return setMsg({ text: 'Файл больше 200 МБ. Выберите короче или сожмите его.', err: true })
    setBusyId(id); setMsg(null)
    try { await api.uploadVideo(id, file); setMsg({ text: 'Видеоинструкция загружена.' }); await load() }
    catch (e) { setMsg({ text: e.message, err: true }) } finally { setBusyId(null) }
  }

  return (
    <>
      <h1>Упражнения и видеоинструкции</h1>
      <p className="muted">Пациент увидит видео перед началом упражнения. Новая загрузка заменяет прежнее видео.</p>
      {msg && <div className={`msg ${msg.err ? 'err' : ''}`} role="status">{msg.text}</div>}
      {!list ? <p className="muted">Загрузка…</p> : list.map((x) => (
        <div className="panel" key={x.id}>
          <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3>{x.title}</h3>
              <span className={`tag ${x.type}`}>{TYPES[x.type]}</span>{' '}
              <span className="muted">{x.video_url ? 'видео загружено' : 'видео нет'}</span>
            </div>
            <label className="btn" style={{ margin: 0, cursor: 'pointer' }}>
              {busyId === x.id ? 'Загружаем…' : x.video_url ? 'Заменить видео' : 'Загрузить видео'}
              <input type="file" accept="video/*" hidden disabled={busyId === x.id} onChange={(e) => upload(x.id, e.target.files[0])} />
            </label>
          </div>
          {x.video_url && <video src={x.video_url} controls width="320" style={{ marginTop: '1rem', borderRadius: 12 }} />}
        </div>
      ))}
    </>
  )
}
