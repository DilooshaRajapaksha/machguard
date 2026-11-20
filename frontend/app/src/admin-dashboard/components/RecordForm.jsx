import PasswordInput from '../../components/PasswordInput'
import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'

export function Field({ label, choices, ...props }) {
  return <label>{label}{choices
    ? <select required {...props}><option value="">Choose…</option>{choices.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
    : props.type === 'password' ? <PasswordInput required {...props} /> : <input required {...props} />}</label>
}

export default function RecordForm({ title, save, children, onSaved }) {
  const { refresh } = useOutletContext()
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function submit(event) {
    event.preventDefault()
    if (busy) return
    const form = event.currentTarget
    setBusy(true)
    setMessage('')
    try {
      await save(Object.fromEntries(new FormData(form)))
      form.reset()
      await refresh()
      setMessage('Saved.')
      onSaved?.()
    } catch (error) { setMessage(error.message) }
    finally { setBusy(false) }
  }
  return <form onSubmit={submit}><h2>{title}</h2><fieldset disabled={busy}>{children}<button>Save</button></fieldset><p role="status">{message}</p></form>
}
