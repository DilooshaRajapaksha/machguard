import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, mustChangePassword, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-slate-50"
        role="status"
        aria-live="polite"
      >
        <p className="text-sm text-slate-600">
          Checking your session…
        </p>
      </div>
    )
  }

  if (!isAuthenticated || mustChangePassword) {
    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: location.pathname + location.search + location.hash,
        }}
      />
    )
  }

  return children ?? <Outlet />
}