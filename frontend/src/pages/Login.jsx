import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { homePathFor } from '../auth/roles'

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to={homePathFor(user)} replace />

  const onSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const loggedIn = await login(form.email, form.password)
      navigate(homePathFor(loggedIn))
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-wrapper">
      <div className="form-card">
        <div className="auth-header">
          <h1>Sign In</h1>
          <p>Enter your campus account credentials to continue</p>
        </div>

        {error && (
          <div className="alert danger" role="alert">
            <i className="fa-solid fa-circle-exclamation" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={onSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              placeholder="name@smartcampus.dev"
              required
              autoComplete="username"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="Enter your password"
              required
              autoComplete="current-password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </div>

          <button type="submit" className="button button-block" style={{ marginTop: '1.25rem' }} disabled={submitting}>
            {submitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.88rem' }}>
          Don&apos;t have an account?{' '}
          <Link to="/register" style={{ fontWeight: 600 }}>
            Register here
          </Link>
        </p>
      </div>
    </div>
  )
}
