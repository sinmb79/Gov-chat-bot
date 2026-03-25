import React, { useEffect, useState } from 'react'
import { listFaqs, createFaq, updateFaq, deleteFaq } from '../api'

const s = {
  title: { fontSize: 22, fontWeight: 700, color: '#1a2540', marginBottom: 20 },
  toolbar: { display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' },
  btn: (color = '#2563eb') => ({
    padding: '8px 16px', background: color, color: '#fff',
    border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
  }),
  table: { width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.07)' },
  th: { padding: '12px 16px', fontSize: 12, fontWeight: 600, color: '#6b7280', textAlign: 'left', background: '#f9fafb', borderBottom: '1px solid #f0f0f0' },
  td: { padding: '12px 16px', fontSize: 14, borderBottom: '1px solid #f5f5f5', verticalAlign: 'top' },
  modal: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
  },
  modalBox: { background: '#fff', borderRadius: 16, padding: '32px 28px', width: 520, maxHeight: '80vh', overflowY: 'auto' },
  label: { display: 'block', fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 },
  input: { width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, marginBottom: 16 },
  textarea: { width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 14, marginBottom: 16, minHeight: 120, resize: 'vertical' },
  err: { color: '#ef4444', fontSize: 13, marginBottom: 12 },
}

function FaqModal({ faq, onClose, onSave }) {
  const [form, setForm] = useState({ question: faq?.question || '', answer: faq?.answer || '', category: faq?.category || '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (faq) await updateFaq(faq.id, form)
      else await createFaq(form)
      onSave()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={s.modal} onClick={onClose}>
      <div style={s.modalBox} onClick={(e) => e.stopPropagation()}>
        <div style={{ fontSize: 17, fontWeight: 700, marginBottom: 20 }}>{faq ? 'FAQ 수정' : 'FAQ 추가'}</div>
        {error && <div style={s.err}>{error}</div>}
        <form onSubmit={submit}>
          <label style={s.label}>카테고리</label>
          <input style={s.input} value={form.category} onChange={set('category')} placeholder="민원, 주민서비스 등" />
          <label style={s.label}>질문 *</label>
          <input style={s.input} value={form.question} onChange={set('question')} required />
          <label style={s.label}>답변 *</label>
          <textarea style={s.textarea} value={form.answer} onChange={set('answer')} required />
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button type="button" style={s.btn('#6b7280')} onClick={onClose}>취소</button>
            <button type="submit" style={s.btn()} disabled={busy}>{busy ? '저장 중...' : '저장'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function FaqPage() {
  const [faqs, setFaqs] = useState([])
  const [editing, setEditing] = useState(null) // null=closed, false=new, obj=edit
  const [error, setError] = useState('')

  const load = () => listFaqs().then(setFaqs).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  const del = async (id) => {
    if (!confirm('삭제하시겠습니까?')) return
    try { await deleteFaq(id); load() } catch (e) { alert(e.message) }
  }

  return (
    <div>
      <div style={s.title}>FAQ 관리</div>
      <div style={s.toolbar}>
        <button style={s.btn()} onClick={() => setEditing(false)}>+ FAQ 추가</button>
        <span style={{ fontSize: 13, color: '#6b7280' }}>총 {faqs.length}개</span>
      </div>
      {error && <div style={s.err}>{error}</div>}
      <table style={s.table}>
        <thead>
          <tr>
            <th style={s.th}>카테고리</th>
            <th style={s.th}>질문</th>
            <th style={s.th}>답변 (일부)</th>
            <th style={s.th}>조회수</th>
            <th style={s.th}>작업</th>
          </tr>
        </thead>
        <tbody>
          {faqs.length === 0 ? (
            <tr><td colSpan={5} style={{ ...s.td, textAlign: 'center', color: '#9ca3af' }}>FAQ가 없습니다.</td></tr>
          ) : faqs.map((f) => (
            <tr key={f.id}>
              <td style={s.td}><span style={{ fontSize: 12, background: '#e0e7ff', color: '#3730a3', padding: '2px 8px', borderRadius: 12 }}>{f.category || '-'}</span></td>
              <td style={{ ...s.td, maxWidth: 200 }}>{f.question}</td>
              <td style={{ ...s.td, maxWidth: 260, color: '#4b5563' }}>{(f.answer || '').slice(0, 60)}{f.answer?.length > 60 ? '...' : ''}</td>
              <td style={s.td}>{f.hit_count ?? 0}</td>
              <td style={s.td}>
                <button style={{ ...s.btn('#f59e0b'), marginRight: 6, padding: '4px 10px' }} onClick={() => setEditing(f)}>수정</button>
                <button style={{ ...s.btn('#ef4444'), padding: '4px 10px' }} onClick={() => del(f.id)}>삭제</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {editing !== null && (
        <FaqModal
          faq={editing || null}
          onClose={() => setEditing(null)}
          onSave={() => { setEditing(null); load() }}
        />
      )}
    </div>
  )
}
