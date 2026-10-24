
 // API-клиент по контракту. VITE_MOCK=true -> данные-заглушки без бэкенда.
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const MOCK = import.meta.env.VITE_MOCK === 'true'

export const getToken = () => localStorage.getItem('token')
export const setToken = (t) => (t ? localStorage.setItem('token', t) : localStorage.removeItem('token'))

async function request(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  if (getToken()) headers.Authorization = `Bearer ${getToken()}`
  if (body) headers['Content-Type'] = 'application/json'
  const res = await fetch(BASE + path, { method, headers, body: form || (body && JSON.stringify(body)) })
  if (res.status === 401) { setToken(null); window.location.href = '/login'; throw new Error('Сессия истекла') }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Что-то пошло не так. Попробуйте ещё раз.')
  }
  return res.json()
}

// ---------- моки ----------
const wait = (v) => new Promise((r) => setTimeout(() => r(v), 250))
const day = (n) => new Date(Date.now() - n * 864e5).toISOString()
const exercises = [
  { id: 1, title: 'Попади в цель', type: 'motor', video_url: null },
  { id: 2, title: 'Повтори слово', type: 'speech', video_url: null },
  { id: 3, title: 'Запомни последовательность', type: 'memory', video_url: null },
  { id: 4, title: 'Пары картинок', type: 'memory', video_url: null },
]
const patients = [
  { id: 1, full_name: 'Иванова Мария Петровна', last_activity: day(0), avg_score: 74, trend: 8 },
  { id: 2, full_name: 'Смирнов Алексей Игоревич', last_activity: day(4), avg_score: 58, trend: -3 },
  { id: 3, full_name: 'Кузнецова Ольга Сергеевна', last_activity: day(1), avg_score: 81, trend: 12 },
]
const results = Array.from({ length: 12 }, (_, i) => {
  const ex = exercises[i % 3]
  return { id: i + 1, exercise_id: ex.id, exercise_title: ex.title, type: ex.type,
    score: 50 + i * 2 + (i % 3) * 4, duration_sec: 90 + i * 5, errors: Math.max(0, 8 - i),
    created_at: day(12 - i), media_url: ex.type === 'speech' ? '' : null, media_type: ex.type === 'speech' ? 'audio' : null }
})
const pw = () => 'Pa-' + Math.random().toString(36).slice(2, 10)
const doctorsDb = [
  { id: 1, full_name: 'Орлова Анна Викторовна', email: 'orlova@clinic.ru', is_active: true, created_at: day(30) },
  { id: 2, full_name: 'Белов Сергей Николаевич', email: 'belov@clinic.ru', is_active: true, created_at: day(10) },
]
const mock = {
  'POST /auth/login': (e) => { localStorage.setItem('mock_email', e); return { access_token: 'mock' } },

  // Тестовые входы:
  // admin@... -> администратор
  // patient@... -> пациент
  // new@... -> врач с обязательной сменой пароля
  // любой другой -> врач
  'GET /me': () => {
    const e = localStorage.getItem('mock_email') || ''
    const admin = e.startsWith('admin')
    const patient = e.startsWith('patient')

    return {
      id: patient ? 1 : 100,
      full_name: admin
        ? 'Администратор больницы'
        : patient
          ? 'Иванова Мария Петровна'
          : 'Доктор Орлова',
      role: admin ? 'admin' : patient ? 'patient' : 'doctor',
      must_change_password: e.startsWith('new') && !localStorage.getItem('mock_changed')
    }
  },

  'POST /auth/change-password': () => { localStorage.setItem('mock_changed', '1'); return { ok: true } },
  'POST /doctor/patients': (d) => ({ id: 99, email: d.email, temp_password: pw() }),
  'POST /doctor/patients/reset': () => ({ temp_password: pw() }),
  'GET /admin/doctors': () => [...doctorsDb],
  'POST /admin/doctors': (d) => { doctorsDb.push({ id: Date.now(), full_name: d.full_name, email: d.email, is_active: true, created_at: day(0) }); return { id: 1, email: d.email, temp_password: pw() } },
  'PATCH /admin/doctors': (d) => { const x = doctorsDb.find((y) => y.id === d.id); if (x) x.is_active = d.is_active; return { ok: true } },
  'POST /admin/doctors/reset': () => ({ temp_password: pw() }),
  'GET /doctor/patients': () => patients,
  'GET /exercises': () => exercises,
  'POST /doctor/assignments': () => ({ ok: true }),
  'POST /doctor/exercises/video': () => ({ video_url: '' }),
  'GET /patients/results': () => results,
  'GET /patients/stats': () => ({ avg_score: 66, trend: 8, sessions_total: 12, completion_rate: 85 }),
  'GET /patients/diary': () => [
    { id: 1, date: day(0), mood: 4, fatigue: 2, note: 'Спала хорошо, упражнения давались легче.' },
    { id: 2, date: day(1), mood: 3, fatigue: 4, note: 'Устала к вечеру, рука дрожала.' },
  ],
}
function call(key, fn, arg) { return MOCK ? wait(mock[key](arg)) : fn() }

// ---------- методы ----------
export const api = {
  login: (email, password) => call('POST /auth/login', () => request('/auth/login', { method: 'POST', body: { email, password } }), email),
  me: () => call('GET /me', () => request('/me')),
  patients: () => call('GET /doctor/patients', () => request('/doctor/patients')),
  exercises: () => call('GET /exercises', () => request('/exercises')),
  assign: (data) => call('POST /doctor/assignments', () => request('/doctor/assignments', { method: 'POST', body: data })),
  uploadVideo: (exerciseId, file) => call('POST /doctor/exercises/video', () => {
    const form = new FormData(); form.append('file', file)
    return request(`/doctor/exercises/${exerciseId}/video`, { method: 'POST', form })
  }),
  results: (id) => call('GET /patients/results', () => request(`/patients/${id}/results`)),
  stats: (id) => call('GET /patients/stats', () => request(`/patients/${id}/stats`)),
  diary: (id) => call('GET /patients/diary', () => request(`/patients/${id}/diary`)),
  changePassword: (old_password, new_password) => call('POST /auth/change-password', () => request('/auth/change-password', { method: 'POST', body: { old_password, new_password } })),
  createPatient: (data) => call('POST /doctor/patients', () => request('/doctor/patients', { method: 'POST', body: data }), data),
  resetPatientPassword: (id) => call('POST /doctor/patients/reset', () => request(`/doctor/patients/${id}/reset-password`, { method: 'POST' })),
  doctors: () => call('GET /admin/doctors', () => request('/admin/doctors')),
  createDoctor: (data) => call('POST /admin/doctors', () => request('/admin/doctors', { method: 'POST', body: data }), data),
  setDoctorActive: (id, is_active) => call('PATCH /admin/doctors', () => request(`/admin/doctors/${id}`, { method: 'PATCH', body: { is_active } }), { id, is_active }),
  resetDoctorPassword: (id) => call('POST /admin/doctors/reset', () => request(`/admin/doctors/${id}/reset-password`, { method: 'POST' })),
}
