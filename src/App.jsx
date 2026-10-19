import { useEffect, useState, createContext, useContext } from 'react'
import { Routes, Route, NavLink, Navigate, Outlet, useNavigate } from 'react-router-dom'
import { api, getToken, setToken } from './api.js'
import Login from './pages/Login.jsx'
import ChangePassword from './pages/ChangePassword.jsx'
import Patients from './pages/Patients.jsx'
import PatientDetail from './pages/PatientDetail.jsx'
import Exercises from './pages/Exercises.jsx'
import Doctors from './pages/Doctors.jsx'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export default function App() {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)
  useEffect(() => {
    if (!getToken()) return setReady(true)
    api.me().then(setUser).catch(() => setToken(null)).finally(() => setReady(true))
  }, [])
  if (!ready) return <p style={{ padding: '2rem' }}>Загрузка…</p>
  const logout = () => { setToken(null); setUser(null) }
  const home = user?.role === 'admin' ? '/admin' : '/doctor'
  const guard = (role, el) => (user?.role === role ? el : <Navigate to={user ? home : '/login'} />)

  return (
    <AuthCtx.Provider value={{ user, setUser, logout }}>
      {user?.must_change_password ? <ChangePassword /> : (
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/doctor" element={guard('doctor', <Layout />)}>
            <Route index element={<Patients />} />
            <Route path="patients/:id" element={<PatientDetail />} />
            <Route path="exercises" element={<Exercises />} />
          </Route>
          <Route path="/admin" element={guard('admin', <Layout />)}>
            <Route index element={<Doctors />} />
          </Route>
          <Route path="*" element={<Navigate to={user ? home : '/login'} />} />
        </Routes>
      )}
    </AuthCtx.Provider>
  )
}

function Layout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  return (
    <div className="shell">
      <nav className="side">
        <div className="brand">Реабилитация</div>
        {user.role === 'admin' ? <NavLink to="/admin" end>Врачи</NavLink> : (
          <>
            <NavLink to="/doctor" end>Пациенты</NavLink>
            <NavLink to="/doctor/exercises">Упражнения и видео</NavLink>
          </>
        )}
        <div className="who">
          {user.full_name}<br />
          <a href="#" onClick={(e) => { e.preventDefault(); logout(); nav('/login') }}>Выйти</a>
        </div>
      </nav>
      <main className="main"><Outlet /></main>
    </div>
  )
}
