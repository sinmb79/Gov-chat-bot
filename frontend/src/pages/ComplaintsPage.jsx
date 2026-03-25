import React, { useEffect, useState } from 'react'
import { listComplaints } from '../api'

const s = {
  title: { fontSize: 22, fontWeight: 700, color: '#1a2540', marginBottom: 20 },
  toolbar: { display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center', flexWrap: 'wrap' },
  select: { padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 13, background: '#fff' },
  table: { width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.07)' },
  th: { padding: '12px 16px', fontSize: 12, fontWeight: 600, color: '#6b7280', textAlign: 'left', background: '#f9fafb', borderBottom: '1px solid #f0f0f0' },
  td: { padding: '12px 16px', fontSize: 13, borderBottom: '1px solid #f5f5f5', verticalAlign: 'middle' },
  badge: (color) => ({
    fontSize: 11, padding: '2px 8px', borderRadius: 12,
    background: color + '20', color: color, fontWeight: 600,
  }),
  note: { fontSize: 12, color: '#9ca3af', marginBottom: 12 },
}

const TIER_COLORS = { A: '#10b981', B: '#3b82f6', C: '#8b5cf6', D: '#f59e0b' }

export default function ComplaintsPage() {
  const [items, setItems] = useState([])
  const [tier, setTier] = useState('')
  const [error, setError] = useState('')

  const load = () =>
    listComplaints({ tier: tier || undefined, limit: 100 })
      .then(setItems)
      .catch((e) => setError(e.message))

  useEffect(() => { load() }, [tier])

  return (
    <div>
      <div style={s.title}>민원 이력</div>
      <div style={s.note}>⚠️ 개인정보 보호 정책에 따라 발화 원문은 마스킹 처리되어 표시됩니다.</div>
      <div style={s.toolbar}>
        <select style={s.select} value={tier} onChange={(e) => setTier(e.target.value)}>
          <option value="">전체 Tier</option>
          <option value="A">Tier A (FAQ)</option>
          <option value="B">Tier B (RAG)</option>
          <option value="C">Tier C (LLM)</option>
          <option value="D">Tier D (폴백)</option>
        </select>
        <span style={{ fontSize: 13, color: '#6b7280' }}>{items.length}건</span>
      </div>
      {error && <div style={{ color: '#ef4444', fontSize: 13, marginBottom: 12 }}>{error}</div>}
      <table style={s.table}>
        <thead>
          <tr>
            <th style={s.th}>시간</th>
            <th style={s.th}>사용자 키 (해시)</th>
            <th style={s.th}>발화 (마스킹)</th>
            <th style={s.th}>Tier</th>
            <th style={s.th}>소스</th>
            <th style={s.th}>응답(ms)</th>
            <th style={s.th}>타임아웃</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr><td colSpan={7} style={{ ...s.td, textAlign: 'center', color: '#9ca3af' }}>이력이 없습니다.</td></tr>
          ) : items.map((item) => (
            <tr key={item.id}>
              <td style={s.td}>{item.created_at ? new Date(item.created_at).toLocaleString('ko-KR') : '-'}</td>
              <td style={{ ...s.td, fontFamily: 'monospace', fontSize: 12 }}>{item.user_key?.slice(0, 12)}...</td>
              <td style={{ ...s.td, maxWidth: 300, color: '#4b5563' }}>{item.utterance_masked || '-'}</td>
              <td style={s.td}>
                <span style={s.badge(TIER_COLORS[item.response_tier] || '#6b7280')}>
                  {item.response_tier || '-'}
                </span>
              </td>
              <td style={s.td}>{item.response_source || '-'}</td>
              <td style={s.td}>{item.response_ms ?? '-'}</td>
              <td style={s.td}>{item.is_timeout ? '⚠️ 예' : '정상'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
