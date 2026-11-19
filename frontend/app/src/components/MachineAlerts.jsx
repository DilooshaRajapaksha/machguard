import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { apiRequest } from '../services/api'

export default function MachineAlerts() {
  const { token } = useAuth()
  const [feed, setFeed] = useState(null)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    let active = true
    let timer
    async function refresh() {
      try {
        const result = await apiRequest('/notifications?unread_only=true&limit=10', { token })
        if (active) { setFeed(result); setError('') }
      } catch (problem) {
        if (active) setError(problem.message)
      } finally {
        if (active) timer = setTimeout(refresh, 5000)
      }
    }
    refresh()
    return () => { active = false; clearTimeout(timer) }
  }, [token, revision])

  async function markRead(id) {
    try {
      await apiRequest('/notifications/' + id + '/read', { token, method: 'POST' })
      setRevision(value => value + 1)
    } catch (problem) { setError(problem.message) }
  }

  return <section className="rounded-md border bg-white p-5">
    <h2 className="text-xl font-semibold">Machine alerts {feed && '(' + feed.unread_count + ' unread)'}</h2>
    {error && <p role="alert">{error}</p>}
    {feed?.items.map(item => <article key={item.id} className="border-t py-3">
      <strong>{item.machine_id} · {item.title}</strong>
      <p>{item.message}</p>
      <small>{new Date(item.reading_timestamp).toLocaleString()} · {item.source}</small>
      <button className="ml-4 underline" onClick={() => markRead(item.id)}>Mark read</button>
    </article>)}
    {feed?.unread_count === 0 && <p>No unread alerts for your machines.</p>}
  </section>
}
