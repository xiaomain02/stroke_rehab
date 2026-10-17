import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import Credentials from '../Credentials.jsx'

export const fmtDate = (d) => new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })

export function Trend({ v }) {
  if (v == null) return <span className="muted">нет данных</span>
  return <span className={v >= 0 ? 'up' : 'down'}>{v >= 0 ? '▲' : '▼'} {Math.abs(v)}%</span>
}

export default function Patients() {
  const [list, setList] = useState(null)
  const [q, setQ] = useState('')
  const [error, setError] = useState('')
  const [form, setForm] = useState(null)
  const [cred, setCred] = useState(null)
  const nav = useNavigate()
  const load = () => api.patients().then(setList).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])
  async function create(e) {
    e.preventDefault(); setError('')
    try { setCred(await api.createPatient(form)); setForm(null); await load() } catch (err) { setError(err.message) }
  }
  const shown = (list || []).filter((p) => p.full_name.toLowerCase().includes(q.toLowerCase()))

  return (
    <>
      <h1>Мои пациенты</h1>
      {error && <div className="msg err" role="alert">{error}</div>}
      {cred && <Credentials data={cred} onClose={() => setCred(null)} />}
      {form ? (
        <form className="panel" onSubmit={create}>
          <h2>Новый пациент</h2>
          <div className="row">
            <label>Имя и фамилия<input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label>
            <label>Эл. почта (будет логином)<input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
            <button>Создать кабинет</button>
            <button type="button" className="ghost" onClick={() => setForm(null)}>Отмена</button>
          </div>
        </form>
      ) : <p><button onClick={() => setForm({ full_name: '', email: '' })}>Добавить пациента</button></p>}
      <div className="panel">
        <label>Поиск по имени<input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Начните вводить фамилию" /></label>
        {!list ? <p className="muted">Загрузка…</p> : shown.length === 0 ? (
          <p className="muted">Пациентов не найдено. Они появятся здесь, когда вы начнёте с ними работать.</p>
        ) : (
          <table>
            <thead><tr><th>Пациент</th><th>Последняя активность</th><th>Средний балл</th><th>Динамика</th></tr></thead>
            <tbody>
              {shown.map((p) => (
                <tr key={p.id} className="link" tabIndex={0} onClick={() => nav(`/doctor/patients/${p.id}`)}
                    onKeyDown={(e) => e.key === 'Enter' && nav(`/doctor/patients/${p.id}`)}>
                  <td><b>{p.full_name}</b></td>
                  <td>{p.last_activity ? fmtDate(p.last_activity) : '—'}</td>
                  <td>{p.avg_score ?? '—'}</td>
                  <td><Trend v={p.trend} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )
}
