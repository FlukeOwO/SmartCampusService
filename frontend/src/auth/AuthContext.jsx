import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, tokens } from '../api/client'
import { STAFF_ROLES } from './roles'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // true จนกว่าจะรู้ว่ามี session เดิมอยู่หรือไม่ (กันหน้า login กระพริบ)
  const [loading, setLoading] = useState(Boolean(tokens.access))

  const logout = useCallback(() => {
    tokens.clear()
    setUser(null)
  }, [])

  useEffect(() => {
    if (!tokens.access) return
    api('/auth/me')
      .then(setUser)
      .catch(() => tokens.clear())
      .finally(() => setLoading(false))
  }, [])

  // refresh token หมดอายุ -> client แจ้งมา ให้กลับไปหน้า login
  useEffect(() => {
    window.addEventListener('auth:expired', logout)
    return () => window.removeEventListener('auth:expired', logout)
  }, [logout])

  const login = useCallback(async (email, password) => {
    const result = await api('/auth/login', { method: 'POST', json: { email, password }, auth: false })
    tokens.set(result)
    setUser(result.user)
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
      login,
      logout,
      register,
      isStaff: Boolean(user && STAFF_ROLES.includes(user.role)),
      isAdmin: user?.role === 'admin',
    }),
    [user, loading, login, logout, register],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
