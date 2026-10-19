import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid, ResponsiveContainer } from 'recharts'
import { api } from '../api.js'
import { fmtDate, Trend } from './Patients.jsx'
import Credentials from '../Credentials.jsx'

const TYPES = { motor: 'Моторика', speech: 'Речь', memory: 'Память' }
const COLORS = { motor: '#5b8a68', speech: '#5f9c9a', memory: '#c9a85c' }

export default function PatientDetail() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [cred, setCred] = useState(null)

  useEffect(() => {
    Promise.all([api.results(id), api.stats(id), api.diary(id), api.exercises()])
      .then(([results, stats, diary, exercises]) => setData({ results, stats, diary, exercises }))
      .catch((e) => setError(e.message))
  }, [id])

  if (error) return <div className="msg err">{error}</div>
  if (!data) return <p className="muted">Загрузка…</p>
  const { results, stats, diary, exercises } = data

  // точки графика: по одной на дату, баллы по типам упражнений
  const byDate = {}
  ;[...results].sort((a, b) => new Date(a.created_at) - new Date(b.created_at)).forEach((r) => {
    const k = fmtDate(r.created_at)
    byDate[k] = { ...(byDate[k] || { date: k }), [r.type]: r.score }
  })
  const chart = Object.values(byDate)

  return (
    <>
      <p><Link to="/doctor">← Все пациенты</Link></p>
      <h1>Карточка пациента</h1>
      <p>
        <button className="ghost" onClick={async () => {
          if (!confirm('Выдать пациенту новый пароль? Старый перестанет работать.')) return
          try { setCred(await api.resetPatientPassword(id)) } catch (e) { setError(e.message) }
        }}>Сбросить пароль пациента</button>
      </p>
      {cred && <Credentials data={cred} onClose={() => setCred(null)} />}

      <div className="grid" style={{ marginBottom: '1.2rem' }}>
        <div className="stat"><b>{stats.avg_score}</b><span>средний балл</span></div>
        <div className="stat"><b><Trend v={stats.trend} /></b><span>динамика за период</span></div>
        <div className="stat"><b>{stats.sessions_total}</b><span>занятий всего</span></div>
        <div className="stat"><b>{stats.completion_rate}%</b><span>выполнено из назначенного</span></div>
      </div>

      <div className="panel">
        <h2>Динамика результатов</h2>
        {chart.length === 0 ? <p className="muted">Результатов пока нет.</p> : (
          <div style={{ height: 300 }}>
            <ResponsiveContainer>
              <LineChart data={chart}>
                <CartesianGrid stroke="#e0ebe0" strokeDasharray="3 3" />
                <XAxis dataKey="date" stroke="#64756a" />
                <YAxis domain={[0, 100]} stroke="#64756a" />
                <Tooltip /><Legend formatter={(v) => TYPES[v]} />
                {Object.keys(TYPES).map((t) => (
                  <Line key={t} type="monotone" dataKey={t} name={t} stroke={COLORS[t]} strokeWidth={2.5} connectNulls dot={{ r: 3 }} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <AssignForm patientId={id} exercises={exercises} />

      <div className="panel">
        <h2>Прохождения и записи</h2>
        {results.length === 0 ? <p className="muted">Пока пусто.</p> : (
          <table>
            <thead><tr><th>Дата</th><th>Упражнение</th><th>Балл</th><th>Ошибки</th><th>Время</th><th>Запись</th></tr></thead>
            <tbody>
              {[...results].reverse().map((r) => (
                <tr key={r.id}>
                  <td>{fmtDate(r.created_at)}</td>
                  <td>{r.exercise_title} <span className={`tag ${r.type}`}>{TYPES[r.type]}</span></td>
                  <td><b>{r.score}</b></td>
                  <td>{r.errors}</td>
                  <td>{Math.floor(r.duration_sec / 60)}:{String(r.duration_sec % 60).padStart(2, '0')}</td>
                  <td>{r.media_type === 'video' ? <video src={r.media_url} controls width="200" />
                     : r.media_type === 'audio' ? <audio src={r.media_url} controls /> : <span className="muted">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <h2>Дневник самочувствия</h2>
        {diary.length === 0 ? <p className="muted">Записей пока нет.</p> : diary.map((d) => (
          <div className="diary" key={d.id}>
            <b>{fmtDate(d.date)}</b> <span className="muted">· настроение {d.mood}/5, усталость {d.fatigue}/5</span>
            <div>{d.note}</div>
          </div>
        ))}
      </div>
    </>
  )
}

function AssignForm({ patientId, exercises }) {
  const [form, setForm] = useState({ exercise_id: exercises[0]?.id || '', due_date: '', times_per_week: 3 })
  const [msg, setMsg] = useState(null)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault(); setMsg(null)
    try {
      await api.assign({ patient_id: Number(patientId), exercise_id: Number(form.exercise_id),
        due_date: form.due_date || null, times_per_week: Number(form.times_per_week) })
      setMsg({ text: 'Упражнение назначено.' })
    } catch (err) { setMsg({ text: err.message, err: true }) }
  }

  return (
    <form className="panel" onSubmit={submit}>
      <h2>Назначить упражнение</h2>
      {msg && <div className={`msg ${msg.err ? 'err' : ''}`} role="status">{msg.text}</div>}
      <div className="row">
        <label>Упражнение
          <select value={form.exercise_id} onChange={set('exercise_id')}>
            {exercises.map((x) => <option key={x.id} value={x.id}>{x.title} ({TYPES[x.type]})</option>)}
          </select>
        </label>
        <label>Раз в неделю<input type="number" min="1" max="14" value={form.times_per_week} onChange={set('times_per_week')} /></label>
        <label>Выполнить до<input type="date" value={form.due_date} onChange={set('due_date')} /></label>
        <button>Назначить</button>
      </div>
    </form>
  )
}
