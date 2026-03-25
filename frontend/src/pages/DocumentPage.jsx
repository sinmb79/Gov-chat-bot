import React, { useEffect, useState, useRef } from 'react'
import { listDocs, uploadDoc, approveDoc, deleteDoc } from '../api'

const s = {
  title: { fontSize: 22, fontWeight: 700, color: '#1a2540', marginBottom: 20 },
  toolbar: { display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' },
  btn: (color = '#2563eb') => ({
    padding: '8px 16px', background: color, color: '#fff',
    border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
  }),
  table: { width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 12, overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.07)' },
  th: { padding: '12px 16px', fontSize: 12, fontWeight: 600, color: '#6b7280', textAlign: 'left', background: '#f9fafb', borderBottom: '1px solid #f0f0f0' },
  td: { padding: '12px 16px', fontSize: 14, borderBottom: '1px solid #f5f5f5', verticalAlign: 'middle' },
  err: { color: '#ef4444', fontSize: 13, marginBottom: 12 },
  badge: (color) => ({
    fontSize: 11, padding: '2px 8px', borderRadius: 12,
    background: color + '20', color: color, fontWeight: 600,
  }),
}

const STATUS_COLOR = {
  pending: '#f59e0b',
  processed: '#10b981',
  parse_failed: '#ef4444',
  embedding_unavailable: '#8b5cf6',
}

export default function DocumentPage() {
  const [docs, setDocs] = useState([])
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef()

  const load = () => listDocs().then(setDocs).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    try {
      await uploadDoc(file)
      load()
    } catch (err) {
      alert('업로드 실패: ' + err.message)
    } finally {
      setUploading(false)
      fileRef.current.value = ''
    }
  }

  const approve = async (id) => {
    try { await approveDoc(id); load() } catch (e) { alert(e.message) }
  }

  const del = async (id) => {
    if (!confirm('삭제하시겠습니까?')) return
    try { await deleteDoc(id); load() } catch (e) { alert(e.message) }
  }

  return (
    <div>
      <div style={s.title}>문서 관리</div>
      <div style={s.toolbar}>
        <button style={s.btn()} onClick={() => fileRef.current.click()} disabled={uploading}>
          {uploading ? '업로드 중...' : '+ 문서 업로드'}
        </button>
        <input ref={fileRef} type="file" accept=".txt,.pdf,.docx,.md" style={{ display: 'none' }} onChange={handleUpload} />
        <span style={{ fontSize: 13, color: '#6b7280' }}>총 {docs.length}개 · txt, pdf, docx, md 지원</span>
      </div>
      {error && <div style={s.err}>{error}</div>}
      <table style={s.table}>
        <thead>
          <tr>
            <th style={s.th}>파일명</th>
            <th style={s.th}>상태</th>
            <th style={s.th}>활성</th>
            <th style={s.th}>업로드일</th>
            <th style={s.th}>작업</th>
          </tr>
        </thead>
        <tbody>
          {docs.length === 0 ? (
            <tr><td colSpan={5} style={{ ...s.td, textAlign: 'center', color: '#9ca3af' }}>문서가 없습니다.</td></tr>
          ) : docs.map((d) => (
            <tr key={d.id}>
              <td style={s.td}>{d.filename}</td>
              <td style={s.td}>
                <span style={s.badge(STATUS_COLOR[d.status] || '#6b7280')}>{d.status}</span>
              </td>
              <td style={s.td}>{d.is_active ? '✅ 활성' : '⏸ 비활성'}</td>
              <td style={s.td}>{d.created_at ? new Date(d.created_at).toLocaleDateString('ko-KR') : '-'}</td>
              <td style={s.td}>
                {!d.is_active && d.status === 'processed' && (
                  <button style={{ ...s.btn('#10b981'), marginRight: 6, padding: '4px 10px' }} onClick={() => approve(d.id)}>승인</button>
                )}
                <button style={{ ...s.btn('#ef4444'), padding: '4px 10px' }} onClick={() => del(d.id)}>삭제</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
