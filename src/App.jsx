
import {
  useEffect,
  useState,
  createContext,
  useContext
} from 'react'

import {
  Routes,
  Route,
  NavLink,
  Navigate,
  Outlet,
  useNavigate
} from 'react-router-dom'

import { api, getToken, setToken } from './api.js'

// Авторизация
import Login from './pages/Login.jsx'
import ChangePassword from './pages/ChangePassword.jsx'

// Врач
import Patients from './pages/Patients.jsx'
import PatientDetail from './pages/PatientDetail.jsx'
import Exercises from './pages/Exercises.jsx'

// Администратор
import Doctors from './pages/Doctors.jsx'

// Пациент
import PatientDashboard from './patient/pages/PatientDashboard.jsx'
import PatientDiary from './patient/pages/PatientDiary.jsx'
import PatientProgress from './patient/pages/PatientProgress.jsx'

// Упражнения пациента
import MovingTargets from './patient/exercises/MovingTargets.jsx'
import SpeechRepeat from './patient/exercises/SpeechRepeat.jsx'
import MemorySequence from './patient/exercises/MemorySequence.jsx'
import MatchingPairs from './patient/exercises/MatchingPairs.jsx'
import VideoRecording from './patient/exercises/VideoRecording.jsx'

const AuthCtx = createContext(null)

export const useAuth = () => useContext(AuthCtx)

export default function App() {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!getToken()) {
      setReady(true)
      return
    }

    api.me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true))
  }, [])

  if (!ready) {
    return <p style={{ padding: '2rem' }}>Загрузка…</p>
  }

  function logout() {
    setToken(null)
    setUser(null)
  }

  const home =
    user?.role === 'admin'
      ? '/admin'
      : user?.role === 'patient'
        ? '/patient'
        : '/doctor'

  function guard(role, element) {
    return user?.role === role
      ? element
      : (
        <Navigate
          to={user ? home : '/login'}
          replace
        />
      )
  }

  return (
    <AuthCtx.Provider value={{ user, setUser, logout }}>
      {user?.must_change_password ? (
        <ChangePassword />
      ) : (
        <Routes>
          {/* Авторизация */}
          <Route path="/login" element={<Login />} />

          {/* Врач */}
          <Route
            path="/doctor"
            element={guard('doctor', <Layout />)}
          >
            <Route index element={<Patients />} />
            <Route
              path="patients/:id"
              element={<PatientDetail />}
            />
            <Route
              path="exercises"
              element={<Exercises />}
            />
          </Route>

          {/* Администратор */}
          <Route
            path="/admin"
            element={guard('admin', <Layout />)}
          >
            <Route index element={<Doctors />} />
          </Route>

          {/* Пациент */}
          <Route
            path="/patient"
            element={guard('patient', <PatientLayout />)}
          >
            <Route
              index
              element={<PatientDashboard />}
            />
            <Route
              path="targets"
              element={<MovingTargets />}
            />
            <Route
              path="speech"
              element={<SpeechRepeat />}
            />
            <Route
              path="memory"
              element={<MemorySequence />}
            />
            <Route
              path="pairs"
              element={<MatchingPairs />}
            />
            <Route
              path="video"
              element={<VideoRecording />}
            />
            <Route
              path="diary"
              element={<PatientDiary />}
            />
            <Route
              path="progress"
              element={<PatientProgress />}
            />
          </Route>

          {/* Временные маршруты для тестирования */}
          <Route
            path="/patient-preview"
            element={<PatientDashboard />}
          />
          <Route
            path="/patient-preview/targets"
            element={<MovingTargets />}
          />
          <Route
            path="/patient-preview/speech"
            element={<SpeechRepeat />}
          />
          <Route
            path="/patient-preview/memory"
            element={<MemorySequence />}
          />
          <Route
            path="/patient-preview/pairs"
            element={<MatchingPairs />}
          />
          <Route
            path="/patient-preview/video"
            element={<VideoRecording />}
          />
          <Route
            path="/patient-preview/diary"
            element={<PatientDiary />}
          />
          <Route
            path="/patient-preview/progress"
            element={<PatientProgress />}
          />

          {/* Перенаправление */}
          <Route
            path="*"
            element={
              <Navigate
                to={user ? home : '/login'}
                replace
              />
            }
          />
        </Routes>
      )}
    </AuthCtx.Provider>
  )
}

// Меню врача и администратора
function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout(event) {
    event.preventDefault()
    logout()
    navigate('/login')
  }

  return (
    <div className="shell">
      <nav className="side">
        <div className="brand">Реабилитация</div>

        {user.role === 'admin' ? (
          <NavLink to="/admin" end>
            Врачи
          </NavLink>
        ) : (
          <>
            <NavLink to="/doctor" end>
              Пациенты
            </NavLink>
            <NavLink to="/doctor/exercises">
              Упражнения и видео
            </NavLink>
          </>
        )}

        <div className="who">
          {user.full_name}
          <br />
          <a href="/login" onClick={handleLogout}>
            Выйти
          </a>
        </div>
      </nav>

      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}

// Интерфейс пациента
function PatientLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="patient-layout">
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
          padding: '20px 32px',
          background: '#eee8fa'
        }}
      >
        <NavLink
          to="/patient"
          style={{
            color: '#59479c',
            fontSize: '22px',
            fontWeight: 'bold',
            textDecoration: 'none'
          }}
        >
          Реабилитация
        </NavLink>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '20px'
          }}
        >
          <span>{user?.full_name}</span>

          <button
            type="button"
            className="patient-button"
            style={{ width: 'auto' }}
            onClick={handleLogout}
          >
            Выйти
          </button>
        </div>
      </header>

      <Outlet />
    </div>
  )
}
