import { useEffect, useState } from 'react'
import { api } from '../api.js'
import Credentials from '../Credentials.jsx'
import { fmtDate } from './Patients.jsx'

export default function Doctors() {
  const [list, setList] = useState(null)
  const [form, setForm] = useState({ full_name: '', email: '' })
  const [cred, setCred] = useState(null)
  const [error, setError] = useState('')
  const load = () => api.doctors().then(setList).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])
  const act = (fn) => async () => { setError(''); try { await fn(); await load() } catch (e) { setError(e.message) } }

  async function create(e) {
    e.preventDefault(); setError('')
    try { setCred(await api.createDoctor(form)); setForm({ full_name: '', email: '' }); await load() }
    catch (err) { setError(err.message) }
  }

  return (
    <>
      <h1>Врачи больницы</h1>
      {error && <div className="msg err" role="alert">{error}</div>}
      {cred && <Credentials data={cred} onClose={() => setCred(null)} />}
      <form className="panel" onSubmit={create}>
        <h2>Добавить врача</h2>
        <div className="row">
          <label>Имя и фамилия<input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label>
          <label>Эл. почта (будет логином)<input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
          <button>Создать аккаунт</button>
        </div>
      </form>
      <div className="panel">
        {!list ? <p className="muted">Загрузка…</p> : list.length === 0 ? <p className="muted">Врачей пока нет. Добавьте первого выше.</p> : (
          <table>
            <thead><tr><th>Врач</th><th>Почта</th><th>Создан</th><th>Статус</th><th></th></tr></thead>
            <tbody>
              {list.map((d) => (
                <tr key={d.id}>
                  <td><b>{d.full_name}</b></td><td>{d.email}</td><td>{fmtDate(d.created_at)}</td>
                  <td>{d.is_active ? <span className="tag">работает</span> : <span className="tag memory">отключён</span>}</td>
                  <td>
                    <div className="row" style={{ gap: '.5rem' }}>
                      <button className="ghost" onClick={act(async () => {
                        if (confirm('Выдать новый пароль? Старый перестанет работать.')) setCred({ email: d.email, ...(await api.resetDoctorPassword(d.id)) })
                      })}>Сбросить пароль</button>
                      <button className="ghost" onClick={act(() => api.setDoctorActive(d.id, !d.is_active))}>{d.is_active ? 'Отключить' : 'Включить'}</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )
}
