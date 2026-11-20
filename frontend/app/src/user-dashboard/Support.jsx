import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { apiRequest } from '../services/api'

export default function Support({ admin = false }) {
  const { token, user } = useAuth()
  const [tickets, setTickets] = useState(null)
  const [machines, setMachines] = useState([])

  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [version, setVersion] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    const options = { token, signal: controller.signal }
    apiRequest('/support', options).then(setTickets).catch(e => { if (!controller.signal.aborted) setError(e.message) })
    if (!admin) {
      const path = user.role === 'admin' ? '/equipment' : '/engineer/me'
      apiRequest(path, options).then(data => setMachines(data.machines || data)).catch(e => { if (!controller.signal.aborted) setError(e.message) })
    }
    return () => controller.abort()
  }, [token, user.role, admin, version])

  async function save(event, id) {
    event.preventDefault()
    if (busy) return
    const form = event.currentTarget
    const body = Object.fromEntries(new FormData(form))
    setError('')
    setBusy(true)
    try {
      await apiRequest(id ? '/support/' + id : '/support', { token, method: id ? 'PATCH' : 'POST', body })
      if (!id) form.reset()
      setVersion(v => v + 1)
    } catch (problem) { setError(problem.message) }
    finally { setBusy(false) }
  }

  return <div className={admin ? "support-desk" : "support-desk support-workspace"}>
    <h1>{admin ? 'Support requests' : 'Support'}</h1>

    {!admin && <form onSubmit={e => save(e)}><h2>New support request</h2>
      <label>Machine<select name="machine_id"><option value="">General help</option>{machines.map(m => <option key={m.machine_id} value={m.machine_id}>{m.name}</option>)}</select></label>
      <label>Subject<input required maxLength={120} name="subject" /></label>
      <label>Description<textarea required maxLength={4000} name="description" /></label>
      <button disabled={busy}>Send request</button>
    </form>}
    <div className="request-list">
    {!admin && <h2>My requests</h2>}
    {error && <p role="alert">{error}</p>}
    {!tickets && !error && <p>Loading requests…</p>}
    {tickets?.length === 0 && <p>No support requests yet.</p>}
    {tickets?.map(t => <article key={t.id}>
      <strong>#{t.id} · {t.subject}</strong><p>{t.full_name} · {t.machine_id || 'General help'} · {new Date(t.created).toLocaleString()}</p>
      <p>{t.description}</p><strong className={admin ? undefined : "ticket-status"} data-state={t.status}>{t.status}</strong>
      {admin ? <form onSubmit={e => save(e, t.id)}>
        <label>Status<select name="status" defaultValue={t.status}>{['Open','In progress','Resolved'].map(s => <option key={s}>{s}</option>)}</select></label>
        <label>Admin reply<textarea name="reply" maxLength={4000} defaultValue={t.reply} /></label>
        <button disabled={busy}>Save response</button>
      </form> : t.reply && <p>Admin reply: {t.reply}</p>}
    </article>)}
    </div>
  </div>
}
