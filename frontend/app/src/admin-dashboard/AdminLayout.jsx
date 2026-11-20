import { useCallback, useEffect, useState } from 'react'
import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiRequest } from '../services/api'
import Navbar from '../components/layout/Navbar'
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
  if (user.role !== 'admin') return <main className="mg-admin">
    <h1>Admin sign-in required</h1>
    <p>You are signed in as {user.username}. Switch accounts to open the admin panel.</p>
    <button type="button" onClick={signOut}>Sign out and use an admin account</button>
    <p><Link to="/">Return to dashboard</Link></p>
  </main>
  return <div className="harbor-shell">
    <Navbar admin />
    <div className="mg-admin"><main>
    <button onClick={refresh}>Refresh</button>
    {error && <p role="alert">{error}</p>}
    {registry ? <Outlet context={{ registry, request, refresh }} /> : !error && <p>Loading registry…</p>}
    </main></div></div>
}
