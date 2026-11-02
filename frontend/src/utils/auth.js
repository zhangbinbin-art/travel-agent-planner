import { reactive } from 'vue'

function decodeToken(token) {
  try {
    const part = token.split('.')[1]
    if (!part) return null
    const base64 = part.replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
    const binary = atob(padded)
    const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0))
    const json = new TextDecoder('utf-8').decode(bytes)
    return JSON.parse(json)
  } catch (e) {
    return null
  }
}

export const auth = reactive({
  token: '',
  role: '',
  auditStatus: '',
  userId: null,
  username: ''
})

export function loadAuth() {
  const token = localStorage.getItem('token') || ''
  if (!token) {
    auth.token = ''
    auth.role = ''
    auth.auditStatus = ''
    auth.userId = null
    auth.username = ''
    return
  }
  const payload = decodeToken(token)
  if (!payload || (payload.exp && payload.exp * 1000 <= Date.now())) {
    clearAuth()
    return
  }
  auth.token = token
  auth.role = payload.role || 'user'
  auth.auditStatus = localStorage.getItem('audit_status') || 'approved'
  auth.userId = payload.sub ? Number(payload.sub) : null
  auth.username = localStorage.getItem('username') || ''
}

export function setAuth(token, username, auditStatus) {
  localStorage.setItem('token', token)
  if (username) {
    localStorage.setItem('username', username)
  }
  if (auditStatus) {
    localStorage.setItem('audit_status', auditStatus)
  }
  loadAuth()
  if (username) {
    auth.username = username
  }
}

export function clearAuth() {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  localStorage.removeItem('audit_status')
  auth.token = ''
  auth.role = ''
  auth.auditStatus = ''
  auth.userId = null
  auth.username = ''
}

export function isLoggedIn() {
  return !!auth.token
}

export function isAdmin() {
  return auth.role === 'admin'
}

export function isApprovedMerchant() {
  return auth.role === 'merchant' && auth.auditStatus === 'approved'
}

loadAuth()
