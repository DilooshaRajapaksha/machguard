import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiRequest } from '../services/api'

export default function WarningPopup({ admin }) {
  const { token, user } = useAuth()
  const [alert, setAlert] = useState(null)
  useEffect(() => {
    const controller = new AbortController()
    let timer
    const key = 'warning-shown-' + user.id
    async function poll() {
      try {
        const feed = await apiRequest('/notifications?unread_only=true&limit=50', { token, signal: controller.signal })
        const warning = feed.items.find(n => ['watch','warning','fault'].includes(n.severity))
        if (!controller.signal.aborted) {
          setAlert(current => feed.items.some(n => n.id === current?.id) ? current : null)
          if (warning && warning.id > Number(sessionStorage.getItem(key) || 0)) {
            sessionStorage.setItem(key, String(warning.id))
            setAlert(warning)
          }
        }
      } catch { setAlert(null) }
      finally { if (!controller.signal.aborted) timer = setTimeout(poll, 5000) }
    }
    poll()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [token, user.id])
  if (!alert) return null
  return createPortal(<div className="warning-toast" role="alert"><strong>{alert.machine_id} · {alert.title}</strong><p>{alert.message}</p>
    <Link to={admin ? '/admin/notifications' : '/notifications'} onClick={() => setAlert(null)}>View notifications</Link>
    <button onClick={() => setAlert(null)} aria-label="Dismiss warning">×</button></div>, document.body)
}
