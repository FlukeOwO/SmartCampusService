import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import { homePathFor } from './auth/roles'
import Layout from './components/Layout'
import { Loading, RouteErrorBoundary } from './components/ui'
import Login from './pages/Login'
import Notifications from './pages/Notifications'
import Register from './pages/Register'
import StaffBookings from './pages/staff/Bookings'
import StaffDashboard from './pages/staff/Dashboard'
import StaffEquipment from './pages/staff/Equipment'
import StaffRequests from './pages/staff/Requests'
import StaffRooms from './pages/staff/Rooms'
import StaffUsers from './pages/staff/Users'
import BookingHistory from './pages/student/BookingHistory'
import CreateRequest from './pages/student/CreateRequest'
import MyRequests from './pages/student/MyRequests'
import Resources from './pages/student/Resources'
import StudentDashboard from './pages/student/Dashboard'

/** กันหน้าตาม role (ฝั่ง backend ตรวจสิทธิ์ซ้ำอีกชั้นเสมอ) */
function RequireRole({ roles, children }) {
  const { user, loading } = useAuth()
  if (loading) return <Loading />
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to={homePathFor(user)} replace />
  return children
}

function Home() {
  const { user, loading } = useAuth()
  if (loading) return <Loading />
  return <Navigate to={user ? homePathFor(user) : '/login'} replace />
}

const STUDENT = ['student']
const STAFF = ['staff', 'admin']

export default function App() {
  return (
    <RouteErrorBoundary>
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        <Route path="/student" element={<RequireRole roles={STUDENT}><StudentDashboard /></RequireRole>} />
        <Route path="/student/requests" element={<RequireRole roles={STUDENT}><MyRequests /></RequireRole>} />
        <Route path="/student/requests/new" element={<RequireRole roles={STUDENT}><CreateRequest /></RequireRole>} />
        <Route path="/student/resources" element={<RequireRole roles={STUDENT}><Resources /></RequireRole>} />
        <Route path="/student/bookings" element={<RequireRole roles={STUDENT}><BookingHistory /></RequireRole>} />

        <Route path="/staff" element={<RequireRole roles={STAFF}><StaffDashboard /></RequireRole>} />
        <Route path="/staff/requests" element={<RequireRole roles={STAFF}><StaffRequests /></RequireRole>} />
        <Route path="/staff/bookings" element={<RequireRole roles={STAFF}><StaffBookings /></RequireRole>} />
        <Route path="/staff/rooms" element={<RequireRole roles={STAFF}><StaffRooms /></RequireRole>} />
        <Route path="/staff/equipment" element={<RequireRole roles={STAFF}><StaffEquipment /></RequireRole>} />
        <Route path="/staff/users" element={<RequireRole roles={['admin']}><StaffUsers /></RequireRole>} />

        <Route path="/notifications" element={<RequireRole><Notifications /></RequireRole>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
    </RouteErrorBoundary>
  )
}
