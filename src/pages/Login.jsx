
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setToken } from '../api.js'
import { useAuth } from '../App.jsx'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const { setUser } = useAuth()
  const nav = useNavigate()

  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('')
    try {
      const { access_token } = await api.login(email, password)
      setToken(access_token)
      const me = await api.me()

      if (!['doctor', 'admin', 'patient'].includes(me.role)) {
        setToken(null)
        throw new Error('У вашей учётной записи нет доступа к системе.')
      }

      setUser(me)

      nav(
        me.role === 'admin'
          ? '/admin'
          : me.role === 'patient'
            ? '/patient'
            : '/doctor'
      )
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login">
      <form className="panel" onSubmit={submit}>
        <h1>Система реабилитации</h1>

        <p className="muted">
          Войдите в личный кабинет пациента, врача
          или администратора больницы.
          Используйте выданные вам учётные данные.
        </p>

        {error && (
          <div className="msg err" role="alert">
            {error}
          </div>
        )}

        <label>
          Эл. почта
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <label>
          Пароль
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        <button disabled={busy}>
          {busy ? 'Входим…' : 'Войти'}
        </button>
      </form>
    </div>
  )
}
