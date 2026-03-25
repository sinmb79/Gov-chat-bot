const BASE = '/api'

function getToken() {
  return localStorage.getItem('token')
}

async function request(method, path, body) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    return null
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || '오류가 발생했습니다.')
  }

  if (res.status === 204) return null
  return res.json()
}

// Auth
export const login = (tenant_id, email, password) =>
  request('POST', '/admin/auth/login', { tenant_id, email, password })

// Metrics
export const getMetrics = () => request('GET', '/admin/metrics')

// FAQ
export const listFaqs = () => request('GET', '/admin/faqs')
export const createFaq = (data) => request('POST', '/admin/faqs', data)
export const updateFaq = (id, data) => request('PUT', `/admin/faqs/${id}`, data)
export const deleteFaq = (id) => request('DELETE', `/admin/faqs/${id}`)

// Documents
export const listDocs = () => request('GET', '/admin/documents')
export const approveDoc = (id) => request('POST', `/admin/documents/${id}/approve`)
export const deleteDoc = (id) => request('DELETE', `/admin/documents/${id}`)
export const uploadDoc = async (file) => {
  const token = getToken()
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${BASE}/admin/documents/upload`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: fd,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || '업로드 실패')
  }
  return res.json()
}

// Complaints
export const listComplaints = (params = {}) => {
  const qs = new URLSearchParams()
  if (params.tier) qs.set('tier', params.tier)
  if (params.limit) qs.set('limit', params.limit)
  return request('GET', `/admin/complaints?${qs}`)
}

// Moderation
export const listRestrictions = () => request('GET', '/admin/moderation')
export const escalateUser = (user_key) => request('POST', `/admin/moderation/${user_key}/escalate`)
export const releaseUser = (user_key) => request('POST', `/admin/moderation/${user_key}/release`)

// Simulator
export const simulate = (tenant_id, utterance) =>
  request('POST', '/engine/query', { tenant_id, utterance, user_key: 'simulator' })
