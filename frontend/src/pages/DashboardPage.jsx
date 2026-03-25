import React, { useEffect, useState } from 'react'
import { getMetrics } from '../api'

const s = {
  title: { fontSize: 22, fontWeight: 700, color: '#1a2540', marginBottom: 20 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, marginBottom: 28 },
  card: {
    background: '#fff', borderRadius: 12, padding: '20px 22px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
  },
  cardLabel: { fontSize: 12, color: '#6b7280', marginBottom: 6, fontWeight: 500 },
  cardVal: { fontSize: 28, fontWeight: 700, color: '#1a2540' },
  cardSub: { fontSize: 12, color: '#9ca3af', marginTop: 2 },
  tierGrid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 28 },
  tierCard: (color) => ({
    background: '#fff', borderRadius: 12, padding: '16px 18px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.07)', borderTop: `3px solid ${color}`,
  }),
  sectionTitle: { fontSize: 15, fontWeight: 700, color: '#374151', marginBottom: 14 },
  err: { color: '#6b7280', fontSize: 14 },
}

const TIER_COLORS = { A: '#10b981', B: '#3b82f6', C: '#8b5cf6', D: '#f59e0b' }
const TIER_LABELS = { A: 'FAQ 직접 응답', B: 'RAG 템플릿', C: 'LLM 재서술', D: '폴백 안내' }

export default function DashboardPage() {
  const [metrics, setMetrics] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getMetrics()
      .then(setMetrics)
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <div style={s.err}>메트릭 로드 실패: {error}</div>
  if (!metrics) return <div style={s.err}>로딩 중...</div>

  const total = metrics.total_count || 0
  const tierCounts = metrics.tier_counts || {}
  const rate = (n) => total ? Math.round(n / total * 100) : 0

  return (
    <div>
      <div style={s.title}>대시보드</div>

      <div style={s.grid}>
        <div style={s.card}>
          <div style={s.cardLabel}>총 민원 수</div>
          <div style={s.cardVal}>{total.toLocaleString()}</div>
          <div style={s.cardSub}>누적</div>
        </div>
        <div style={s.card}>
          <div style={s.cardLabel}>자동 응답률</div>
          <div style={s.cardVal}>{rate((tierCounts.A || 0) + (tierCounts.B || 0) + (tierCounts.C || 0))}%</div>
          <div style={s.cardSub}>A+B+C Tier</div>
        </div>
        <div style={s.card}>
          <div style={s.cardLabel}>FAQ 응답률</div>
          <div style={s.cardVal}>{rate(tierCounts.A || 0)}%</div>
          <div style={s.cardSub}>Tier A</div>
        </div>
        <div style={s.card}>
          <div style={s.cardLabel}>타임아웃</div>
          <div style={s.cardVal}>{metrics.timeout_count || 0}</div>
          <div style={s.cardSub}>4.5초 초과</div>
        </div>
      </div>

      <div style={s.sectionTitle}>Tier별 분류</div>
      <div style={s.tierGrid}>
        {['A', 'B', 'C', 'D'].map((t) => (
          <div key={t} style={s.tierCard(TIER_COLORS[t])}>
            <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>Tier {t} — {TIER_LABELS[t]}</div>
            <div style={{ fontSize: 26, fontWeight: 700, color: '#1a2540' }}>{tierCounts[t] || 0}</div>
            <div style={{ fontSize: 12, color: '#9ca3af' }}>{rate(tierCounts[t] || 0)}%</div>
          </div>
        ))}
      </div>
    </div>
  )
}
