import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const s = {
  page: {
    minHeight: '100vh', display: 'flex', alignItems: 'center',
    justifyContent: 'center', background: '#f5f6fa',
  },
  card: {
    background: '#fff', borderRadius: 16, padding: '40px 36px',
    width: 380, boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
  },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 4, color: '#1a2540' },
  sub: { fontSize: 13, color: '#6b7280', marginBottom: 28 },
  label: { display: 'block', fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 },
  input: {
    width: '100%', padding: '10px 12px', border: '1px solid #d1d5db',
    borderRadius: 8, fontSize: 14, outline: 'none', marginBottom: 16,
  },
  btn: {
    width: '100%', padding: '12px', background: '#2563eb', color: '#fff',
    border: 'none', borderRadius: 8, fontSize: 15, fontWeight: 600,
    cursor: 'pointer', marginTop: 4,
  },
  err: { color: '#ef4444', fontSize: 13, marginTop: 12, textAlign: 'center' },
}

export default function LoginPage() {
  const [form, setForm] = useState({ tenant_id: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(form.tenant_id, form.email, form.password)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>🏛️</div>
        <div style={s.title}>GovBot KR</div>
        <div style={s.sub}>관리자 로그인</div>
        <form onSubmit={submit}>
          <label style={s.label}>기관 ID (tenant_id)</label>
          <input style={s.input} value={form.tenant_id} onChange={set('tenant_id')} required placeholder="dongducheon" />
          <label style={s.label}>이메일</label>
          <input style={s.input} type="email" value={form.email} onChange={set('email')} required placeholder="admin@example.com" />
          <label style={s.label}>비밀번호</label>
          <input style={s.input} type="password" value={form.password} onChange={set('password')} required />
          <button style={s.btn} type="submit" disabled={busy}>
            {busy ? '로그인 중...' : '로그인'}
          </button>
        </form>
        {error && <div style={s.err}>{error}</div>}
      </div>
    </div>
  )
}
