/**
 * API client - คุยกับ FastAPI backend
 *
 * - URL ของ API มาจาก VITE_API_BASE_URL (local: http://localhost:8000/api/v1, cloud: URL ของ Cloud Run)
 * - แนบ access token ทุก request; ถ้าได้ 401 จะขอ token ใหม่ด้วย refresh token แล้วลองซ้ำ 1 ครั้ง
 * - error ทุกชนิดถูกแปลงเป็น ApiError { status, message, details } ตามรูปแบบของ backend
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(
  /\/$/,
  '',
)

const ACCESS_KEY = 'sc_access_token'
const REFRESH_KEY = 'sc_refresh_token'

export class ApiError extends Error {
  constructor(status, message, details = null) {
    super(message)
    this.status = status
    this.details = details
  }
}

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  set({ access_token, refresh_token }) {
    if (access_token) localStorage.setItem(ACCESS_KEY, access_token)
    if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

function buildUrl(path, params) {
  const url = new URL(BASE_URL + path)
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value)
  })
  return url
}

async function parseError(response) {
  let body = null
  try {
    body = await response.json()
  } catch {
    // ไม่ใช่ JSON (เช่น proxy error)
  }
  const message = body?.message || `Request failed (${response.status})`
  return new ApiError(response.status, message, body?.details ?? null)
}

let refreshing = null

async function refreshAccessToken() {
  // ถ้ามีหลาย request ได้ 401 พร้อมกัน ให้ขอ token ใหม่แค่ครั้งเดียว
  if (!refreshing) {
    refreshing = (async () => {
      const refresh = tokens.refresh
      if (!refresh) return false
      const response = await fetch(buildUrl('/auth/refresh'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      })
      if (!response.ok) return false
      tokens.set(await response.json())
      return true
    })().finally(() => {
      refreshing = null
    })
  }
  return refreshing
}

/**
 * @param {string} path เช่น '/requests/me'
 * @param {{method?: string, json?: object, form?: FormData, params?: object, auth?: boolean}} options
 */
export async function api(path, { method = 'GET', json, form, params, auth = true } = {}, retry = true) {
  const headers = {}
  if (json !== undefined) headers['Content-Type'] = 'application/json'
  if (auth && tokens.access) headers.Authorization = `Bearer ${tokens.access}`

  let response
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: json !== undefined ? JSON.stringify(json) : form,
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Please check that the backend is running.')
  }

  if (response.status === 401 && auth && retry && tokens.refresh) {
    if (await refreshAccessToken()) return api(path, { method, json, form, params, auth }, false)
    tokens.clear()
    window.dispatchEvent(new Event('auth:expired'))
  }
  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return null
  return response.json()
}

/** ดึง list ทั้งหมดในหน้าเดียว (สูงสุด 100 รายการ ตามเพดานของ API) */
export async function listAll(path, params = {}) {
  const page = await api(path, { params: { page_size: 100, ...params } })
  return page.items
}
