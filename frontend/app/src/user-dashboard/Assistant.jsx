import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { apiRequest } from '../services/api'
import './Assistant.css'

const starters = ['Explain the latest machine warning.', 'Summarize this machine’s readings.']

export default function Assistant() {
  const { token, user } = useAuth()
  const [picker, setPicker] = useState(false)
  const pickerRef = useRef(null)
  const triggerRef = useRef(null)
  function closePicker() {
    setPicker(false)
    triggerRef.current?.focus()
  }
  useEffect(() => {
    if (!picker) return
    function dismiss(event) {
      if (!pickerRef.current?.contains(event.target)) setPicker(false)
    }
    document.addEventListener('pointerdown', dismiss)
    document.addEventListener('focusin', dismiss)
    return () => {
      document.removeEventListener('pointerdown', dismiss)
      document.removeEventListener('focusin', dismiss)
    }
  }, [picker])
  const [history, setHistory] = useState([])
  const [machines, setMachines] = useState([])
  const [configured, setConfigured] = useState(null)
  const [id, setId] = useState(null)
  const [machine, setMachine] = useState('')
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [context, setContext] = useState(null)
  const [estimate, setEstimate] = useState(null)
  const [energyError, setEnergyError] = useState('')
  const bottom = useRef(null)
  const active = useRef(null)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all(['/chat/status', '/chat/conversations', '/chat/machines'].map(path => apiRequest(path, { token, signal: controller.signal })))
      .then(([status, conversations, units]) => { setConfigured(status.configured); setHistory(conversations); setMachines(units) })
      .catch(err => { if (err.name !== 'AbortError') setError(err.message) })
    return () => { controller.abort(); active.current?.abort() }
  }, [token])

  useEffect(() => { bottom.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }) }, [messages, busy])

  function startNew() {
    setId(null); setMessages([]); setContext(null); setDraft(''); setError('')
  }

  async function openConversation(nextId) {
    setBusy(true); setError('')
    const controller = new AbortController()
    active.current = controller
    try {
      const data = await apiRequest(`/chat/conversations/${nextId}`, { token, signal: controller.signal })
      setId(data.id); setMachine(data.machine_id || ''); setMessages(data.messages); setContext(null); setDraft('')
    } catch (err) { if (err.name !== 'AbortError') setError(err.message) }
    finally { setBusy(false) }
  }

  async function send(event) {
    event.preventDefault()
    if (busy || !draft.trim()) return
    const message = draft.trim()
    setBusy(true); setError('')
    const controller = new AbortController()
    active.current = controller
    try {
      const data = await apiRequest('/chat/messages', {
        method: 'POST', token, signal: controller.signal, timeoutMs: 65000,
        body: { message, conversation_id: id, machine_id: machine || null },
      })
      setMessages(previous => [...previous, { role: 'user', content: message }, { role: 'assistant', content: data.reply }])
      setId(data.conversation_id); setContext(data.context); setDraft('')
      if (!id) setHistory(previous => [{ id: data.conversation_id, title: message.slice(0, 80) }, ...previous])
    } catch (err) { if (err.name !== 'AbortError') setError(err.message) }
    finally { setBusy(false) }
  }

  async function calculate(event) {
    event.preventDefault()
    const values = Object.fromEntries(new FormData(event.currentTarget))
    setEnergyError(''); setEstimate(null)
    try {
      setEstimate(await apiRequest('/chat/energy', { method: 'POST', token, body: {
        energy_kwh: Number(values.energy), production_units: Number(values.output),
        emission_factor: Number(values.factor), factor_source: values.source,
      } }))
    } catch (err) { setEnergyError(err.message) }
  }

  return (
    <div className="maintenance-assistant night-chat">
      <header className="assistant-heading"><h1>MachGuard Assistant</h1></header>
      <div className="assistant-workspace">
        <aside className="conversation-list" aria-label="Conversations">
          <button className="desk-button" onClick={startNew} disabled={busy}>+ New conversation</button>
          <h2>Recent conversations</h2>
          {!history.length && <p className="muted">Your conversations will appear here.</p>}
          {history.map(item => <button key={item.id} className={item.id === id ? 'conversation active' : 'conversation'} disabled={busy} onClick={() => openConversation(item.id)}>{item.title}</button>)}
        </aside>
        <section className="chat-desk" aria-label="Maintenance chat">

          {configured === false && <p className="desk-notice">Chat needs a backend API key and model. Add GEMINI_API_KEY and GEMINI_MODEL to backend/.env, then reload this page. The calculator works without them.</p>}
          <div className="chat-transcript" aria-live="polite" aria-busy={busy}>
            {!messages.length && <div className="chat-empty"><span className="chat-compass" aria-hidden="true">&#10043;</span><h2>How can I help, {(user?.full_name || user?.username || 'engineer').split(' ')[0]}?</h2><p>Choose a machine for context, or ask a general question. Follow-up questions stay in this conversation.</p>{starters.map(text => <button disabled={busy} key={text} onClick={() => setDraft(text)}>{text} <span aria-hidden="true">↗</span></button>)}</div>}
            {messages.map((message, index) => <article className={`chat-message ${message.role}`} key={index}><p className="message-author">{message.role === 'user' ? 'You' : 'MachGuard'}</p><p className="message-content">{message.content}</p></article>)}
            {busy && <p className="muted" role="status">Working on it…</p>}<div ref={bottom} />
          </div>
          {context?.machine_id && <div className="desk-notice">{context.machine_id} · {context.source} · {context.message || context.received_at}</div>}
          {error && <p className="desk-error" role="alert">{error}</p>}
          <form className="chat-compose" onSubmit={send}><label htmlFor="chat-message" className="sr-only">Your question</label><textarea id="chat-message" value={draft} onChange={event => setDraft(event.target.value)} placeholder="Ask a question…" maxLength={4000} rows={3} disabled={busy} required /><div className="composer-actions">
            <div className="picker-anchor" ref={pickerRef} onKeyDown={event => {
              if (event.key === 'Escape') closePicker()
            }}>
              <button ref={triggerRef} type="button" aria-label="Choose machine" aria-expanded={picker} onClick={() => setPicker(!picker)}>+ <span>{machine || 'Machine'}</span></button>
              {picker && <div className="machine-options" role="group" aria-label="Machine selection">
                {id ? <small>Start a new conversation to change machine.</small> :
                  ['', ...new Set([...machines, ...(machine ? [machine] : [])])].map(value =>
                    <button key={value} type="button" disabled={busy} aria-pressed={value === machine} onClick={() => {
                      setMachine(value)
                      closePicker()
                    }}>{value || 'General question'}</button>
                  )}
              </div>}
            </div><button className="desk-button" disabled={busy || configured !== true || !draft.trim()}>Send &uarr;</button></div><small>Messages and selected readings are sent to Google Gemini. Use only sample data with the free tier. Prototype advice needs engineer review; no machine controls are changed.</small></form>
        </section>
      </div>
      <details className="energy-desk"><summary>Energy calculator</summary><p>Use energy and useful output from the same period. Enter an applicable electricity emission factor and its source. This estimates emissions, not savings.</p>
        <form onSubmit={calculate} onChange={() => setEstimate(null)}>
          <label>Energy (kWh)<input name="energy" type="number" step="any" min="0" max="1000000000" required /></label>
          <label>Useful output (units)<input name="output" type="number" step="any" min="0.000001" max="1000000000000" required /></label>
          <label>Factor (kg CO₂e/kWh)<input name="factor" type="number" step="any" min="0" max="100" required /></label>
          <label>Factor source and year<input name="source" minLength={3} maxLength={300} placeholder="Publication, year or URL" required /></label>
          <button className="desk-button">Calculate estimate</button>
        </form>
        {energyError && <p role="alert" className="desk-error">{energyError}</p>}
        {estimate && <output className="energy-result">Estimated electricity emissions: <strong>{estimate.estimated_kg_co2e} kg CO₂e</strong> · Energy per output unit: <strong>{estimate.kwh_per_unit} kWh</strong><small>{estimate.basis}</small></output>}
      </details>
    </div>
  )
}
