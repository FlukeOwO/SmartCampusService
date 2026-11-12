import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, isTransient, tokens } from '../api/client'
import { Loading, ServerUnavailable } from '../components/ui'
import { STAFF_ROLES } from './roles'

const AuthContext = createContext(null)

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [bootError, setBootError] = useState(null)
  // true จนกว่าจะรู้ว่ามี session เดิมอยู่หรือไม่ (กันหน้า login กระพริบ)
  const [loading, setLoading] = useState(Boolean(tokens.access))

  const logout = useCallback(() => {
    tokens.clear()
    setUser(null)
    setBootError(null)
  }, [])

  const applySession = useCallback(async () => {
    try {
      setUser(await api('/auth/me'))
      setBootError(null)
    } catch (err) {
      // 401 = session หมดจริง. เครือข่ายล่ม / 503 ระหว่าง cold start ต้องเก็บ token ไว้แล้วให้กดลองใหม่
      if (err.status === 401) {
        tokens.clear()
        setUser(null)
        setBootError(null)
      } else {
        setUser(null)
        setBootError(err)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!tokens.access) return undefined
    let cancelled = false
    api('/auth/me')
      .then((me) => {
        if (cancelled) return
        setUser(me)
        setBootError(null)
      })
      .catch((err) => {
        if (cancelled) return
        if (err.status === 401) {
          tokens.clear()
          setUser(null)
          setBootError(null)
        } else {
          setUser(null)
          setBootError(err)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const retryBoot = useCallback(() => {
    setLoading(true)
    setBootError(null)
    applySession()
  }, [applySession])

  // refresh token หมดอายุ -> client แจ้งมา ให้กลับไปหน้า login
  useEffect(() => {
    window.addEventListener('auth:expired', logout)
    return () => window.removeEventListener('auth:expired', logout)
  }, [logout])

  const login = useCallback(async (email, password) => {
    const send = () => api('/auth/login', { method: 'POST', json: { email, password }, auth: false })
    let result
    try {
      result = await send()
    } catch (err) {
      if (!isTransient(err)) throw err
      await delay(1200)
      result = await send()
    }
    tokens.set(result)
    setUser(result.user)
    setBootError(null)
    return result.user
  }, [])

  const register = useCallback(
    (data) => api('/auth/register', { method: 'POST', json: data, auth: false }),
    [],
  )

  const value = useMemo(
    () => ({
      user,
      loading,
      bootError,
      retryBoot,
      login,
      logout,
      register,
      isStaff: Boolean(user && STAFF_ROLES.includes(user.role)),
      isAdmin: user?.role === 'admin',
    }),
    [user, loading, bootError, retryBoot, login, logout, register],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/** ระหว่างเช็ค session หรือเซิร์ฟเวอร์ยังไม่ตื่น อย่าเด้งไปหน้า login (จะดูเหมือนหน้าเปิดไม่ได้) */
export function AuthGate({ children }) {
  const { loading, bootError, retryBoot } = useAuth()
  if (bootError) {
    return (
      <main className="container">
        <ServerUnavailable error={bootError} onRetry={retryBoot} />
      </main>
    )
  }
  if (loading) {
    return (
      <main className="container">
        <Loading
          text="Loading..."
          slowText="The server is waking up. This can take a few seconds after it has been idle."
        />
      </main>
    )
  }
  return children
}

// eslint-disable-next-line react/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
