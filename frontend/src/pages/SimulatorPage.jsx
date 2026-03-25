import React, { useState, useRef, useEffect } from 'react'
import { simulate } from '../api'
import { useAuth } from '../contexts/AuthContext'

const TIER_COLOR = { A: '#10b981', B: '#3b82f6', C: '#8b5cf6', D: '#f59e0b' }

const s = {
  title: { fontSize: 22, fontWeight: 700, color: '#1a2540', marginBottom: 20 },
  wrap: { display: 'flex', gap: 20, height: 'calc(100vh - 180px)' },
  chatArea: {
    flex: 1, background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.07)',
    display: 'flex', flexDirection: 'column', overflow: 'hidden',
  },
  messages: { flex: 1, overflowY: 'auto', padding: '20px 20px 0' },
  inputRow: {
    display: 'flex', gap: 10, padding: '16px',
    borderTop: '1px solid #f0f0f0',
  },
  input: {
    flex: 1, padding: '10px 14px', border: '1px solid #d1d5db',
    borderRadius: 24, fontSize: 14, outline: 'none',
  },
  sendBtn: {
    padding: '10px 20px', background: '#2563eb', color: '#fff',
    border: 'none', borderRadius: 24, fontSize: 14, fontWeight: 600, cursor: 'pointer',
  },
  msg: (role) => ({
    marginBottom: 16,
    display: 'flex',
    flexDirection: role === 'user' ? 'row-reverse' : 'row',
    alignItems: 'flex-end', gap: 8,
  }),
  bubble: (role) => ({
    maxWidth: '75%', padding: '10px 14px', borderRadius: role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
    background: role === 'user' ? '#2563eb' : '#f3f4f6',
    color: role === 'user' ? '#fff' : '#1a2540',
    fontSize: 14, lineHeight: 1.5, whiteSpace: 'pre-wrap',
  }),
  meta: { fontSize: 11, color: '#9ca3af', marginTop: 4 },
  sidePanel: { width: 240, background: '#fff', borderRadius: 12, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,0.07)', height: 'fit-content' },
  sideTitle: { fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 12 },
  examples: { listStyle: 'none' },
  exampleBtn: {
    width: '100%', padding: '8px 10px', border: '1px solid #e5e7eb',
    borderRadius: 8, fontSize: 12, cursor: 'pointer', textAlign: 'left',
    background: '#f9fafb', marginBottom: 6, color: '#374151',
  },
}

const EXAMPLES = [
  '주민등록등본은 어디서 발급하나요?',
  '전입신고는 어떻게 하나요?',
  '쓰레기 배출 시간이 어떻게 되나요?',
  '여권 신청 절차를 알려주세요.',
  '민원 담당 전화번호가 뭔가요?',
]

export default function SimulatorPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const { user } = useAuth()
  const bottomRef = useRef()

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async (text) => {
    const utterance = text || input.trim()
    if (!utterance || busy) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: utterance }])
    setBusy(true)
    try {
      const res = await simulate(user.tenant_id, utterance)
      setMessages((m) => [
        ...m,
        {
          role: 'bot',
          text: res.answer,
          tier: res.tier,
          source: res.source,
          ms: res.elapsed_ms,
          citations: res.citations,
        },
      ])
    } catch (err) {
      setMessages((m) => [...m, { role: 'bot', text: '오류: ' + err.message, tier: 'D' }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div style={s.title}>응답 시뮬레이터</div>
      <div style={s.wrap}>
        <div style={s.chatArea}>
          <div style={s.messages}>
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', color: '#9ca3af', marginTop: 40, fontSize: 14 }}>
                질문을 입력하여 민원 응답을 테스트하세요.
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} style={s.msg(m.role)}>
                <div>
                  <div style={s.bubble(m.role)}>{m.text}</div>
                  {m.role === 'bot' && (
                    <div style={s.meta}>
                      <span style={{ color: TIER_COLOR[m.tier], fontWeight: 600 }}>Tier {m.tier}</span>
                      {' · '}{m.source}{m.ms != null ? ` · ${m.ms}ms` : ''}
                      {m.citations?.map((c, j) => (
                        <span key={j}> · 📎 {c.doc}{c.date ? ` (${c.date})` : ''}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {busy && (
              <div style={s.msg('bot')}>
                <div style={{ ...s.bubble('bot'), color: '#9ca3af' }}>응답 중...</div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
          <div style={s.inputRow}>
            <input
              style={s.input}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
              placeholder="질문을 입력하세요 (Enter 전송)"
              disabled={busy}
            />
            <button style={s.sendBtn} onClick={() => send()} disabled={busy}>전송</button>
          </div>
        </div>
        <div style={s.sidePanel}>
          <div style={s.sideTitle}>예시 질문</div>
          <ul style={s.examples}>
            {EXAMPLES.map((ex, i) => (
              <li key={i}>
                <button style={s.exampleBtn} onClick={() => send(ex)}>{ex}</button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
