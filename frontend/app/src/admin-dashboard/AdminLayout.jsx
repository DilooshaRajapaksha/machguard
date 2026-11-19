import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate, NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiRequest } from '../services/api'
import './admin.css'

export default function AdminLayout() {
  const { user, token, signOut } = useAuth()
  const [registry, setRegistry] = useState(null)
  const [error, setError] = useState('')
  const request = useCallback((path, options) => apiRequest(path, { ...options, token }), [token])
  const refresh = useCallback(async () => {
    try {
      setRegistry(await request('/admin/registry'))
      setError('')
    } catch (problem) {
      setError(problem.message)
    }
  }, [request])

  useEffect(() => { if (user.role === 'admin') refresh() }, [refresh, user.role])
  if (user.role !== 'admin') return <Navigate to="/" replace />
  return <div className="mg-admin">
    <header><strong>MechGuard Administration</strong><Link to="/">User dashboard</Link><button onClick={signOut}>Sign out</button></header>
    <main><nav aria-label="Admin pages">{['Home','Machines','Engineers','Reports'].map(page =>
      <NavLink end key={page} to={page === 'Home' ? '/admin' : '/admin/' + page.toLowerCase()}>{page}</NavLink>
    )}<button onClick={refresh}>Refresh</button></nav>
    {error && <p role="alert">{error}</p>}
    {registry ? <Outlet context={{ registry, request, refresh }} /> : !error && <p>Loading registry…</p>}
    </main></div>
}
