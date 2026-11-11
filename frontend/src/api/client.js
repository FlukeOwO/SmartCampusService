/**
 * API client - คุยกับ FastAPI backend
 *
 * - URL ของ API มาจาก VITE_API_BASE_URL (local: http://localhost:8000/api/v1, cloud: URL ของ Cloud Run)
 * - แนบ access token ทุก request; ถ้าได้ 401 จะขอ token ใหม่ด้วย refresh token แล้วลองซ้ำ 1 ครั้ง
 * - error ทุกชนิดถูกแปลงเป็น ApiError { status, message, details } ตามรูปแบบของ backend
 * - GET ที่เจอ cold start (เครือข่ายล่ม, 502/503/504, timeout) ลองใหม่เอง ไม่ล้าง session
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(
  /\/$/,
  '',
)

const ACCESS_KEY = 'sc_access_token'
const REFRESH_KEY = 'sc_refresh_token'
const TRANSIENT = new Set([0, 502, 503, 504])

export class ApiError extends Error {
  constructor(status, message, details = null) {
    super(message)
    this.status = status
    this.details = details
  }
}

export function isTransient(error) {
  return error instanceof ApiError && TRANSIENT.has(error.status)
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

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

const UNREACHABLE = 'Cannot reach the server. It may be waking up — wait a moment and try again.'

async function parseError(response) {
  if (response.status === 413) {
    return new ApiError(
      413,
      'The upload is too large. Keep attachments within the size limit (about 24 MB total).',
    )
  }
  let body = null
  try {
    body = await response.json()
  } catch {
    // ไม่ใช่ JSON (เช่น proxy error หรือหน้า HTML ของ Cloud Run)
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
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), 20000)
      try {
        const response = await fetch(buildUrl('/auth/refresh'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refresh }),
          signal: controller.signal,
        })
        // 401/403 = refresh token ใช้ไม่ได้จริง จึงต้องออกจากระบบ
        // 5xx / เครือข่ายล่ม = เซิร์ฟเวอร์ยังไม่พร้อม ห้ามล้าง token
        if (response.status === 401 || response.status === 403) return false
        if (!response.ok) throw await parseError(response)
        tokens.set(await response.json())
        return true
      } catch (err) {
        if (err instanceof ApiError) throw err
        throw new ApiError(0, UNREACHABLE)
      } finally {
        clearTimeout(timer)
      }
    })().finally(() => {
      refreshing = null
    })
  }
  return refreshing
}

async function apiOnce(path, { method = 'GET', json, form, params, auth = true, timeoutMs } = {}, allowRefresh = true) {
  const headers = {}
  if (json !== undefined) headers['Content-Type'] = 'application/json'
  if (auth && tokens.access) headers.Authorization = `Bearer ${tokens.access}`

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs ?? (form ? 60000 : 20000))
  let response
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: json !== undefined ? JSON.stringify(json) : form,
      signal: controller.signal,
    })
  } catch (err) {
    if (err?.name === 'AbortError') throw new ApiError(0, 'The server is taking too long. It may be waking up — wait a moment and try again.')
    throw new ApiError(0, UNREACHABLE)
  } finally {
    clearTimeout(timer)
  }

  if (response.status === 401 && auth && allowRefresh && tokens.refresh) {
    let refreshed = false
    try {
      refreshed = await refreshAccessToken()
    } catch (err) {
      if (err instanceof ApiError) throw err
      throw new ApiError(0, UNREACHABLE)
    }
    if (refreshed) return apiOnce(path, { method, json, form, params, auth, timeoutMs }, false)
    tokens.clear()
    window.dispatchEvent(new Event('auth:expired'))
  }
  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return null
  try {
    return await response.json()
  } catch {
    throw new ApiError(response.status, 'The server returned an unexpected response. Please try again.')
  }
}

/**
 * @param {string} path เช่น '/requests/me'
 * @param {{method?: string, json?: object, form?: FormData, params?: object, auth?: boolean, timeoutMs?: number}} options
 */
export async function api(path, options = {}, allowRefresh = true) {
  const method = (options.method || 'GET').toUpperCase()
  const attempts = method === 'GET' || method === 'HEAD' ? 3 : 1
  let lastError
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return await apiOnce(path, { ...options, method }, allowRefresh)
    } catch (err) {
      lastError = err
      if (!isTransient(err) || attempt === attempts - 1) throw err
      await delay(800 * (attempt + 1))
    }
  }
  throw lastError
}

/** ดึง list ทั้งหมดในหน้าเดียว (สูงสุด 100 รายการ ตามเพดานของ API) */
export async function listAll(path, params = {}) {
  const page = await api(path, { params: { page_size: 100, ...params } })
  if (!page || !Array.isArray(page.items)) {
    throw new ApiError(0, 'The server returned an unexpected response. Please try again.')
  }
  return page.items
}
