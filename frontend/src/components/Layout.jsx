import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const nav = [
  { to: '/', label: '대시보드', icon: '📊' },
  { to: '/faq', label: 'FAQ 관리', icon: '❓' },
  { to: '/docs', label: '문서 관리', icon: '📄' },
  { to: '/complaints', label: '민원 이력', icon: '📋' },
  { to: '/moderation', label: '악성 감지', icon: '🚫' },
  { to: '/simulator', label: '시뮬레이터', icon: '💬' },
]

const s = {
  wrap: { display: 'flex', minHeight: '100vh' },
  sidebar: {
    width: 220, background: '#1a2540', color: '#e8ecf4', display: 'flex',
    flexDirection: 'column', padding: '0 0 16px',
  },
  brand: {
    padding: '20px 20px 16px', fontSize: 17, fontWeight: 700,
    borderBottom: '1px solid #2d3a5a', letterSpacing: '-0.3px',
  },
  navArea: { flex: 1, padding: '12px 8px' },
  link: (active) => ({
    display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
    borderRadius: 8, marginBottom: 2, textDecoration: 'none', fontSize: 14,
    color: active ? '#fff' : '#9bacd0',
    background: active ? '#2563eb' : 'transparent',
    fontWeight: active ? 600 : 400,
  }),
  userBox: {
    margin: '0 12px', padding: '10px 12px', background: '#2d3a5a',
    borderRadius: 8, fontSize: 12, color: '#9bacd0',
  },
  logoutBtn: {
    marginTop: 6, width: '100%', background: 'none', border: 'none',
    color: '#ef4444', cursor: 'pointer', textAlign: 'left', fontSize: 12, padding: 0,
  },
  main: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'auto' },
  header: {
    background: '#fff', borderBottom: '1px solid #e5e7eb',
    padding: '0 28px', height: 56, display: 'flex', alignItems: 'center',
    fontSize: 14, color: '#6b7280',
  },
  content: { padding: 28, flex: 1 },
}

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div style={s.wrap}>
      <aside style={s.sidebar}>
        <div style={s.brand}>🏛️ GovBot KR</div>
        <nav style={s.navArea}>
          {nav.map(({ to, label, icon }) => (
            <NavLink key={to} to={to} end={to === '/'} style={({ isActive }) => s.link(isActive)}>
              <span>{icon}</span>{label}
            </NavLink>
          ))}
        </nav>
        <div style={s.userBox}>
          <div style={{ marginBottom: 2, color: '#c8d3ea', fontWeight: 600 }}>{user?.email}</div>
          <div>{user?.tenant_id} · {user?.role}</div>
          <button style={s.logoutBtn} onClick={handleLogout}>로그아웃</button>
        </div>
      </aside>
      <div style={s.main}>
        <header style={s.header}>GovBot KR 관리 대시보드</header>
        <main style={s.content}>{children}</main>
      </div>
    </div>
  )
}
