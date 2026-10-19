import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { useAuth } from '../App.jsx'

export default function ChangePassword() {
  const { user, setUser, logout } = useAuth()
  const [f, setF] = useState({ old: '', new1: '', new2: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const nav = useNavigate()
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault(); setError('')
    if (f.new1.length < 8) return setError('Новый пароль должен быть не короче 8 символов.')
    if (f.new1 !== f.new2) return setError('Новые пароли не совпадают.')
    setBusy(true)
    try {
      await api.changePassword(f.old, f.new1)
      setUser({ ...user, must_change_password: false })
      nav(user.role === 'admin' ? '/admin' : '/doctor')
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (
    <div className="login">
      <form className="panel" onSubmit={submit}>
        <h1>Придумайте свой пароль</h1>
        <p className="muted">Вы вошли с временным паролем. Замените его на свой, чтобы продолжить.</p>
        {error && <div className="msg err" role="alert">{error}</div>}
        <label>Временный пароль<input type="password" required value={f.old} onChange={set('old')} /></label>
        <label>Новый пароль (от 8 символов)<input type="password" required value={f.new1} onChange={set('new1')} /></label>
        <label>Повторите новый пароль<input type="password" required value={f.new2} onChange={set('new2')} /></label>
        <div className="row"><button disabled={busy}>{busy ? 'Сохраняем…' : 'Сохранить пароль'}</button>
        <button type="button" className="ghost" onClick={logout}>Выйти</button></div>
      </form>
    </div>
  )
}
