import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { apiRequest } from '../services/api'

export default function MachineAlerts({ preview = false }) {
  const { token } = useAuth()
  const [feed, setFeed] = useState(null)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    let active = true
    let timer
    async function refresh() {
      try {
        const result = await apiRequest(preview ? '/notifications?limit=5' : '/notifications?limit=100', { token })
        if (active) { setFeed(result); setError('') }
      } catch (problem) {
        if (active) setError(problem.message)
      } finally {
        if (active) timer = setTimeout(refresh, 5000)
      }
    }
    refresh()
    return () => { active = false; clearTimeout(timer) }
  }, [token, revision, preview])

  async function markRead(id) {
    try {
      await apiRequest('/notifications/' + id + '/read', { token, method: 'POST' })
      setRevision(value => value + 1)
    } catch (problem) { setError(problem.message) }
  }

  return <section className="dashboard-alerts">
    <header className="flex flex-wrap items-center gap-3">
      <Bell size={20} aria-hidden="true" />
      <h2 className="text-xl font-semibold">Machine notifications</h2>
      {feed && <span className="text-sm">{feed.unread_count} unread</span>}
      {preview && <Link className="ml-auto underline" to="/notifications">View all</Link>}
    </header>
    {error && <p role="alert">{error}</p>}
    {!error && !feed && <p role="status">Loading notifications...</p>}
    {feed?.items.map(item => <article key={item.id} data-severity={item.severity} className="border-t py-3">
      <strong>{item.machine_id} &middot; {item.title}</strong>
      <p>{item.message}</p>
      <small>{new Date(item.reading_timestamp).toLocaleString()} &middot; {item.source}</small>
      <Link className="ml-4 underline" to={'/equipment/' + encodeURIComponent(item.machine_id)}>View machine</Link>
      {!item.is_read && <button className="ml-4 underline" onClick={() => markRead(item.id)}>Mark read</button>}
    </article>)}
    {feed?.items.length === 0 && <p>No notifications in the last 24 hours.</p>}
  </section>
}
