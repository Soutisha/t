export type SessionUser = {
  id: string
  phone_e164: string
  display_name: string
  status: string
  roles: string[]
}

export type AuthSession = {
  access_token: string
  token_type: string
  expires_in: number
  user: SessionUser
}

const TOKEN_KEY = 'pitstop_access_token'
const USER_KEY = 'pitstop_session_user'

export function readSession(): { token: string; user: SessionUser } | null {
  const token = sessionStorage.getItem(TOKEN_KEY)
  const rawUser = sessionStorage.getItem(USER_KEY)
  if (!token || !rawUser) return null
  try {
    return { token, user: JSON.parse(rawUser) as SessionUser }
  } catch {
    clearSession()
    return null
  }
}

export function saveSession(session: AuthSession) {
  sessionStorage.setItem(TOKEN_KEY, session.access_token)
  sessionStorage.setItem(USER_KEY, JSON.stringify(session.user))
}

export function clearSession() {
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(USER_KEY)
}

export async function apiRequest<T>(path: string, options: RequestInit = {}, authenticated = true): Promise<T> {
  const token = sessionStorage.getItem(TOKEN_KEY)
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (authenticated && token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`/api/v1${path}`, { ...options, headers })
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : await response.text()
  if (!response.ok) {
    const message = typeof payload === 'object' && payload && 'detail' in payload
      ? String((payload as { detail: unknown }).detail)
      : `Request failed (${response.status})`
    if (response.status === 401 && authenticated) {
      clearSession()
      window.dispatchEvent(new Event('pitstop:session-expired'))
    }
    throw new Error(message)
  }
  return payload as T
}

export async function downloadCsv(path: string, filename: string) {
  const token = sessionStorage.getItem(TOKEN_KEY)
  const response = await fetch(`/api/v1${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || `Export failed (${response.status})`)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}
