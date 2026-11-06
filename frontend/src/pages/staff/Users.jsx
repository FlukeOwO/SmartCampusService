import { useState } from 'react'
import { api, listAll } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { useDialog } from '../../components/Dialog'
import { useFlash } from '../../components/Flash'
import { EmptyState, ErrorState, Loading, PageHeader, SearchBox } from '../../components/ui'
import { matches } from '../../lib/search'
import { useApi } from '../../lib/useApi'

const ROLES = ['student', 'staff', 'admin']
const EMPTY = { full_name: '', email: '', password: '', role: 'staff', staff_id: '' }

export default function StaffUsers() {
  const { user: me } = useAuth()
  const flash = useFlash()
  const ask = useDialog()
  const [query, setQuery] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const { data, error, loading, reload } = useApi(() => listAll('/auth/users'), [])

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const act = async (fn, message) => {
    try {
      await fn()
      flash(message, 'success')
      reload()
      return true
    } catch (err) {
      flash(err.message, 'danger')
      return false
    }
  }

  // เปลี่ยนสิทธิ์หรือปิดบัญชีมีผลทันที จึงถามยืนยันก่อน
  const changeUser = async (u, patch, title, message, confirmLabel, doneMessage) => {
    const ok = await ask({ title, message, confirmLabel, danger: patch.is_active === false || patch.role === 'admin' })
    if (ok) act(() => api(`/auth/users/${u.id}`, { method: 'PATCH', json: patch }), doneMessage)
  }

  const onCreate = async (e) => {
    e.preventDefault()
    const ok = await act(
      () => api('/auth/users', { method: 'POST', json: { ...form, staff_id: form.staff_id || null } }),
      `Account for ${form.email} created`,
    )
    if (ok) {
      setForm(EMPTY)
      setShowForm(false)
    }
  }

  const rows = (data || []).filter((u) => matches(query, u.full_name, u.email, u.role, u.student_id, u.staff_id))

  return (
    <>
      <PageHeader icon="fa-users-gear" title="User Management" subtitle="Admin only: manage roles and account access.">
        <button type="button" className="button" onClick={() => setShowForm(!showForm)}>
          <i className="fa-solid fa-user-plus" /> Add Staff Account
        </button>
      </PageHeader>

      <div className={`expandable-panel ${showForm ? 'show' : ''}`}>
        <h2 className="section-title" style={{ marginBottom: '1.25rem' }}>Create Staff / Admin Account</h2>
        <form onSubmit={onCreate}>
          <div className="grid grid-3">
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="u-name">Full Name</label>
              <input id="u-name" required value={form.full_name} onChange={set('full_name')} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="u-email">Email</label>
              <input id="u-email" type="email" required value={form.email} onChange={set('email')} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="u-password">Temporary Password</label>
              <input id="u-password" type="password" required minLength={8} autoComplete="new-password" value={form.password} onChange={set('password')} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="u-role">Role</label>
              <select id="u-role" value={form.role} onChange={set('role')}>
                <option value="staff">staff</option>
                <option value="admin">admin</option>
              </select>
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="u-staff-id">Staff ID (optional)</label>
              <input id="u-staff-id" value={form.staff_id} onChange={set('staff_id')} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button type="button" className="button secondary-button button-sm" onClick={() => setShowForm(false)}>
              Cancel
            </button>
            <button type="submit" className="button button-sm">
              <i className="fa-solid fa-check" /> Create Account
            </button>
          </div>
        </form>
      </div>

      <div className="toolbar-container" style={{ marginTop: 0 }}>
        <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
          Total users: <strong>{data?.length ?? 0}</strong>
        </p>
        <SearchBox value={query} onChange={setQuery} placeholder="Search users or email..." />
      </div>

      {error && <ErrorState error={error} onRetry={reload} />}
      {loading ? (
        <Loading />
      ) : (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th style={{ width: 70 }}>ID</th>
                <th>Full Name</th>
                <th>Email Address</th>
                <th>Role</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((u) => (
                <tr key={u.id}>
                  <td>
                    <strong>#{u.id}</strong>
                  </td>
                  <td style={{ fontWeight: 600 }}>
                    <i className="fa-regular fa-circle-user" style={{ color: 'var(--primary)', marginRight: 6 }} />
                    {u.full_name}
                    {u.id === me.id && <span className="role-tag" style={{ marginLeft: 6 }}>you</span>}
                  </td>
                  <td style={{ color: 'var(--text-secondary)' }}>{u.email}</td>
                  <td>
                    <select
                      aria-label={`Role of ${u.email}`}
                      value={u.role}
                      disabled={u.id === me.id}
                      style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}
                      onChange={(e) =>
                        changeUser(
                          u,
                          { role: e.target.value },
                          `Change ${u.full_name} to ${e.target.value}?`,
                          `${u.email} changes from ${u.role} to ${e.target.value} and gets that role's access right away.`,
                          `Make ${e.target.value}`,
                          `${u.full_name} is now ${e.target.value}`,
                        )
                      }
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`${u.email} active`}
                      checked={u.is_active}
                      disabled={u.id === me.id}
                      onChange={(e) =>
                        e.target.checked
                          ? changeUser(u, { is_active: true }, `Activate ${u.full_name}?`, `${u.email} can sign in again.`, 'Activate', `${u.full_name} activated`)
                          : changeUser(
                              u,
                              { is_active: false },
                              `Deactivate ${u.full_name}?`,
                              `${u.email} can no longer sign in. Their requests and bookings stay in the system.`,
                              'Deactivate',
                              `${u.full_name} deactivated`,
                            )
                      }
                    />
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <EmptyState icon="fa-solid fa-users-slash" title="No Users Found" />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
