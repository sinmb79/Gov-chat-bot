import React, { useEffect, useState } from 'react'
import { listRestrictions, escalateUser, releaseUser } from '../api'

const LEVEL_INFO = [
  { label: 'NORMAL', color: '#10b981' },
  { label: 'WARNED', color: '#f59e0b' },
  { label: 'THROTTLED', color: '#f97316' },
  { label: 'SUSPENDED', color: '#ef4444' },
  { label: 'BLOCKED', color: '#7f1d1d' },
  { label: 'BANNED', color: '#1e1e1e' },
]

const s = {
  title: { fontSize: 22, fontWeight: 700, color: '#1a2540', marginBottom: 20 },
  table: { width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.07)' },
  th: { padding: '12px 16px', fontSize: 12, fontWeight: 600, color: '#6b7280', textAlign: 'left', background: '#f9fafb', borderBottom: '1px solid #f0f0f0' },
  td: { padding: '12px 16px', fontSize: 14, borderBottom: '1px solid #f5f5f5', verticalAlign: 'middle' },
  btn: (color = '#2563eb') => ({
    padding: '4px 10px', background: color, color: '#fff',
    border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', marginRight: 6,
  }),
  badge: (color) => ({
    fontSize: 11, padding: '3px 10px', borderRadius: 12,
    background: color + '20', color: color, fontWeight: 700,
  }),
}

export default function ModerationPage() {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')

  const load = () => listRestrictions().then(setItems).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  const escalate = async (user_key) => {
    try { await escalateUser(user_key); load() } catch (e) { alert(e.message) }
  }

  const release = async (user_key) => {
    if (!confirm('제한을 해제하시겠습니까?')) return
    try { await releaseUser(user_key); load() } catch (e) { alert(e.message) }
  }

  return (
    <div>
      <div style={s.title}>악성 감지 · 이용 제한</div>
      {error && <div style={{ color: '#ef4444', fontSize: 13, marginBottom: 12 }}>{error}</div>}
      <table style={s.table}>
        <thead>
          <tr>
            <th style={s.th}>사용자 키</th>
            <th style={s.th}>현재 레벨</th>
            <th style={s.th}>사유</th>
            <th style={s.th}>만료</th>
            <th style={s.th}>작업</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr><td colSpan={5} style={{ ...s.td, textAlign: 'center', color: '#9ca3af' }}>제한 사용자가 없습니다.</td></tr>
          ) : items.map((item) => {
            const info = LEVEL_INFO[item.level] || LEVEL_INFO[0]
            const canRelease = item.level >= 1
            const canEscalate = item.level < 4 // editor can escalate up to SUSPENDED(3)
            return (
              <tr key={item.id}>
                <td style={{ ...s.td, fontFamily: 'monospace', fontSize: 12 }}>{item.user_key}</td>
                <td style={s.td}>
                  <span style={s.badge(info.color)}>{item.level} {info.label}</span>
                </td>
                <td style={s.td}>{item.reason || '-'}</td>
                <td style={s.td}>{item.expires_at ? new Date(item.expires_at).toLocaleString('ko-KR') : '영구'}</td>
                <td style={s.td}>
                  {canEscalate && (
                    <button style={s.btn('#ef4444')} onClick={() => escalate(item.user_key)}>단계 상향</button>
                  )}
                  {canRelease && (
                    <button style={s.btn('#10b981')} onClick={() => release(item.user_key)}>해제</button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
