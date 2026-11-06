import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { homePathFor } from '../auth/roles'
import { useFlash } from '../components/Flash'

export default function Register() {
  const { user, register } = useAuth()
  const flash = useFlash()
  const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', email: '', student_id: '', password: '' })
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to={homePathFor(user)} replace />

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const onSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await register({ ...form, student_id: form.student_id || null })
      flash('Registration successful. Please sign in.', 'success')
      navigate('/login')
    } catch (err) {
      // 422 = รูปแบบไม่ถูก เช่นรหัสผ่านสั้นกว่า 8 ตัว, 409 = อีเมลซ้ำ
      setError(err.status === 422 ? 'Please check the form: password needs at least 8 characters.' : err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-wrapper">
      <div className="form-card">
        <div className="auth-header">
          <h1>Create Account</h1>
          <p>Register to request services and book campus resources</p>
        </div>

        {error && (
          <div className="alert danger" role="alert">
            <i className="fa-solid fa-circle-exclamation" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={onSubmit}>
          <div className="form-group">
            <label htmlFor="full_name">Full Name</label>
            <input id="full_name" type="text" placeholder="e.g. John Doe" required value={form.full_name} onChange={set('full_name')} />
          </div>
          <div className="form-group">
            <label htmlFor="email">Campus Email</label>
            <input id="email" type="email" placeholder="e.g. user@smartcampus.dev" required value={form.email} onChange={set('email')} />
          </div>
          <div className="form-group">
            <label htmlFor="student_id">Student ID (optional)</label>
            <input id="student_id" type="text" placeholder="e.g. 67050885" value={form.student_id} onChange={set('student_id')} />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="At least 8 characters"
              required
              minLength={8}
              autoComplete="new-password"
              value={form.password}
              onChange={set('password')}
            />
          </div>

          <button type="submit" className="button button-block" style={{ marginTop: '1.25rem' }} disabled={submitting}>
            {submitting ? 'Creating account...' : 'Register Now'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.88rem' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ fontWeight: 600 }}>
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
