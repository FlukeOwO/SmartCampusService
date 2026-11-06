import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { FlashMessages, useClearFlash } from './Flash'

const STUDENT_LINKS = [
  { to: '/student', icon: 'fa-house', label: 'หน้าหลัก', end: true },
  { to: '/student/requests', icon: 'fa-bullhorn', label: 'คำร้อง' },
  { to: '/student/resources', icon: 'fa-calendar-plus', label: 'จองห้อง/อุปกรณ์' },
  { to: '/student/bookings', icon: 'fa-clock-rotate-left', label: 'การจองของฉัน' },
]

const STAFF_LINKS = [
  { to: '/staff', icon: 'fa-clipboard-list', label: 'งานที่ต้องทำ', end: true },
  { to: '/staff/requests', icon: 'fa-list-check', label: 'คำร้อง' },
  { to: '/staff/bookings', icon: 'fa-calendar-days', label: 'การจอง' },
  { to: '/staff/rooms', icon: 'fa-door-closed', label: 'ห้อง' },
  { to: '/staff/equipment', icon: 'fa-boxes-stacked', label: 'อุปกรณ์' },
  { to: '/staff/users', icon: 'fa-users-gear', label: 'ผู้ใช้', adminOnly: true },
]

const ROLE_LABEL = { student: 'Student', staff: 'Staff', admin: 'Admin' }
const POLL_MS = 30000

/** จำนวนแจ้งเตือนที่ยังไม่อ่าน: poll ทุก 30 วินาทีตามที่ออกแบบไว้ (เหมาะกับ Cloud Run scale-to-zero) */
function useUnreadCount(enabled) {
  const [unread, setUnread] = useState(0)
  useEffect(() => {
    if (!enabled) return undefined
    let cancelled = false
    const load = () =>
      api('/notifications/stats/summary')
        .then((s) => !cancelled && setUnread(s.unread))
        .catch(() => {})
    load()
    const timer = setInterval(load, POLL_MS)
    window.addEventListener('notifications:changed', load)
    return () => {
      cancelled = true
      clearInterval(timer)
      window.removeEventListener('notifications:changed', load)
    }
  }, [enabled])
  return unread
}

export default function Layout() {
  const { user, isStaff, isAdmin, logout } = useAuth()
  const navigate = useNavigate()
  const unread = useUnreadCount(Boolean(user))
  const clearFlash = useClearFlash()

  const links = (isStaff ? STAFF_LINKS : STUDENT_LINKS).filter((l) => !l.adminOnly || isAdmin)

  const onLogout = () => {
    clearFlash()
    logout()
    navigate('/login')
  }

  return (
    <>
      <nav className="navbar">
        <Link to="/" className="brand">
          <div className="brand-icon">
            <i className="fa-solid fa-graduation-cap" />
          </div>
          <span className="brand-text">Smart Campus</span>
        </Link>

        {user && (
          <div className="nav-links">
            <div className="user-badge">
              <i className="fa-regular fa-circle-user" />
              <span>{user.full_name}</span>
              <span className={`role-tag ${isStaff ? 'admin' : ''}`}>{ROLE_LABEL[user.role]}</span>
            </div>

            {links.map((link) => (
              <NavLink key={link.to} to={link.to} end={link.end}>
                <i className={`fa-solid ${link.icon}`} /> {link.label}
              </NavLink>
            ))}

            <NavLink to="/notifications" className="nav-bell" aria-label={`แจ้งเตือน (${unread} ยังไม่อ่าน)`}>
              <i className="fa-solid fa-bell" />
              {unread > 0 && <span className="bell-count">{unread > 99 ? '99+' : unread}</span>}
            </NavLink>

            <a href="#/login" className="logout-btn" onClick={(e) => (e.preventDefault(), onLogout())}>
              <i className="fa-solid fa-right-from-bracket" /> ออกจากระบบ
            </a>
          </div>
        )}
      </nav>

      <main className="container">
        <FlashMessages />
        <Outlet />
      </main>
    </>
  )
}
