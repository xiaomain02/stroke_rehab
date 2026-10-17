import { useState } from 'react'
// Показывает логин и временный пароль. Пароль виден один раз: на сервере хранится только хеш.
export default function Credentials({ data, onClose }) {
  const [copied, setCopied] = useState(false)
  const text = `${data.email ? `Логин: ${data.email}\n` : ''}Временный пароль: ${data.temp_password}`
  async function copy() {
    try { await navigator.clipboard.writeText(text); setCopied(true) } catch { /* выделите и скопируйте вручную */ }
  }
  return (
    <div className="cred" role="status">
      <h3>Данные для входа</h3>
      {data.email && <div>Логин: <code>{data.email}</code></div>}
      <div>Временный пароль: <code>{data.temp_password}</code></div>
      <p className="muted">Передайте их лично. Пароль показывается один раз; при первом входе его нужно будет сменить. Если потеряется, сбросьте и выдайте новый.</p>
      <div className="row">
        <button onClick={copy}>{copied ? 'Скопировано' : 'Скопировать'}</button>
        <button className="ghost" onClick={onClose}>Готово</button>
      </div>
    </div>
  )
}
