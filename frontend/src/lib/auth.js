import { ACCESS_TOKEN, REFRESH_TOKEN } from '@/constants'

// Return the browser storage object that matches the selected persistence mode.
function getStorage(type) {
  return type === 'local' ? localStorage : sessionStorage
}

// Detect which storage currently owns the active auth session.
function getTokenSource() {
  if (sessionStorage.getItem(REFRESH_TOKEN)) {
    return 'session'
  }
  if (localStorage.getItem(REFRESH_TOKEN)) {
    return 'local'
  }
  if (sessionStorage.getItem(ACCESS_TOKEN)) {
    return 'session'
  }
  if (localStorage.getItem(ACCESS_TOKEN)) {
    return 'local'
  }
  return null
}

// Read the access token from whichever storage currently holds the session.
export function getAccessToken() {
  const source = getTokenSource()
  if (!source) {
    return null
  }
  return getStorage(source).getItem(ACCESS_TOKEN)
}

// Read the refresh token from the active auth storage.
export function getRefreshToken() {
  const source = getTokenSource()
  if (!source) {
    return null
  }
  return getStorage(source).getItem(REFRESH_TOKEN)
}

// Remove all auth tokens from both storage locations to prevent stale sessions.
export function clearAuthTokens() {
  localStorage.removeItem(ACCESS_TOKEN)
  localStorage.removeItem(REFRESH_TOKEN)
  sessionStorage.removeItem(ACCESS_TOKEN)
  sessionStorage.removeItem(REFRESH_TOKEN)
}

// Save a fresh login session into either local or session storage as one unit.
export function setAuthTokens({ access, refresh, persist }) {
  const source = persist ? 'local' : 'session'
  const storage = getStorage(source)

  clearAuthTokens()
  storage.setItem(ACCESS_TOKEN, access)
  storage.setItem(REFRESH_TOKEN, refresh)
}

// Replace only the access token while keeping it in the same storage as the active session.
export function updateAccessToken(access) {
  const source = getTokenSource() ?? 'local'
  const storage = getStorage(source)
  const otherStorage = getStorage(source === 'local' ? 'session' : 'local')

  storage.setItem(ACCESS_TOKEN, access)
  otherStorage.removeItem(ACCESS_TOKEN)
}
