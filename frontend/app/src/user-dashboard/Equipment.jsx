import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiRequest } from '../services/api'
import BenchReadings from '../components/BenchReadings'

const base = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const time = value => new Date(value).toLocaleString()

function download(blob, name) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function EquipmentDirectory() {
  const { token } = useAuth()
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    apiRequest('/equipment', {token, signal:controller.signal}).then(setItems).catch(e => {
      if (!controller.signal.aborted) setError(e.message)
    })
    return () => controller.abort()
  }, [token])
  return <section className="rounded border bg-white p-5"><h2 className="font-bold">Registered machines</h2>
    {error && <p role="alert">{error}</p>}
    {items.map(m => <p key={m.machine_id}><Link className="underline" to={'/equipment/'+encodeURIComponent(m.machine_id)}>{m.name}</Link> Â· {m.status}</p>)}
    {!items.length && !error && <p>No registered machines to display.</p>}
  </section>
}

export default function Equipment() {
  const { code } = useParams()
  return <EquipmentRecord key={code} code={code} />
}

function EquipmentRecord({ code }) {
  const { token } = useAuth()
  const path = '/equipment/'+encodeURIComponent(code)
  const [data,setData] = useState(null)
  const [message,setMessage] = useState('')
  const [reply,setReply] = useState(null)
  const [busy,setBusy] = useState(false)
  const [revision,setRevision] = useState(0)
  useEffect(() => {
    let active = true
    let timer
    async function load() {
      try {
        const result = await apiRequest(path,{token})
        if (active) setData(result)
      } catch (e) {
        if (active) { setData(null); setMessage(e.message) }
      } finally { if (active) timer=setTimeout(load,10000) }
    }
    load()
    return () => {active=false; clearTimeout(timer)}
  },[token,path,revision])

  async function submit(event, action) {
    event.preventDefault()
    if (busy) return
    const form=event.currentTarget
    const values=Object.fromEntries(new FormData(form))
    setBusy(true)
    try {
      if (action==='manuals') {
        const response=await fetch(base+path+'/manuals/'+values.kind+'?name='+encodeURIComponent(values.file.name)+'&excerpt='+encodeURIComponent(values.excerpt),{
          method:'PUT',headers:{Authorization:'Bearer '+token},body:values.file
        })
        if (!response.ok) throw new Error((await response.json()).detail)
      } else if (action === 'guidance') {
        setReply(await apiRequest(path+'/guidance',{token,method:'POST',body:values}))
        setMessage('')
        return
      } else {
        if (action==='services' && !values.due) values.due=null
        await apiRequest(path+'/'+action,{token,method:action==='services'?'POST':'PUT',body:values})
      }
      if (action!=='notes') form.reset()
      setMessage('Saved.')
      setRevision(r=>r+1)
    } catch(e) {setMessage(e.message)} finally {setBusy(false)}
  }

  async function getManual(manual) {
    try {
      const response=await fetch(base+path+'/manuals/'+manual.kind,{headers:{Authorization:'Bearer '+token}})
      if (!response.ok) throw new Error('Unable to download this manual.')
      download(await response.blob(),manual.name)
    } catch(e) {setMessage(e.message)}
  }

  if (!data) return <p role="status">{message || 'Loading machineâ€¦'}</p>
  const {machine,notes,forecast,can_edit:allowed}=data
  const last=data.services?.[0]
  const notesFields=[['description','Description'],['probe_location','Probe location'],['operating_load','Operating load'],['approved_range','Approved operating range and reference']]
  const comparable=forecast?.predicted ? data.services?.find(s=>/temperatur|overheat|hot/i.test(s.symptom)) : null
  return <main className="space-y-5 [&_section]:rounded [&_section]:border [&_section]:bg-white [&_section]:p-5 [&_h2]:font-bold [&_label]:block [&_input]:m-1 [&_input]:border [&_textarea]:border [&_button]:underline">
    <h1 className="text-2xl font-bold">{machine.name}</h1>
    <p>{code} Â· {machine.model} Â· {machine.location} Â· {machine.status} Â· Engineer: {machine.engineer || 'Unassigned'}</p>
    <section>{notesFields.map(([key,label])=><p key={key}>{label}: {notes[key] || 'Unrecorded'}</p>)}</section>
    <BenchReadings machineId={code} showHistory={allowed} />
    <section><h2>Surface probe 1 Â· 15-minute forecast</h2>
      {forecast ? <><p>Issued {time(forecast.issued)} for {time(forecast.due)}. Projected {forecast.projected_c.toFixed(1)} Â°C against a {forecast.limit_c} Â°C limit.</p><p>Expected crossing: {forecast.predicted?'Yes':'No'}. Observation: {forecast.result}.</p></> : <p>Awaiting a configured limit and at least one minute of continuous probe data below it.</p>}
      {comparable && <p>Review the temperature-related repair on {comparable.serviced}. Reported symptom: {comparable.symptom}. Recorded outcome: {comparable.outcome}.</p>}
    </section>
    {allowed && <><section><h2>Service and repair history</h2>
      <p>Last recorded service: {last?.serviced || 'Unrecorded'} Â· Next service: {last?.due || 'Unscheduled'}</p>
      {data.services.map(s=><p key={s.id}>{s.serviced} Â· {s.symptom} Â· {s.outcome} Â· {s.author}</p>)}
      {data.reports.map((r,i)=><p key={i}>{r.title} Â· {r.notes} Â· {r.created_by}</p>)}
      <button onClick={async()=>{try {const current=await apiRequest(path,{token}); if(!current.can_edit) throw new Error('Assignment required.'); download(new Blob([JSON.stringify({machine:code,services:current.services,reports:current.reports},null,2)],{type:'application/json'}),code+'-report.json')}catch(e){setMessage(e.message)}}}>Download maintenance report</button>
      <form onSubmit={e=>submit(e,'services')}><label>Service date<input required type="date" name="serviced"/></label><label>Next service<input type="date" name="due"/></label><label>Symptom<input required minLength={2} name="symptom"/></label><label>Repair and outcome<textarea required minLength={2} name="outcome"/></label><button disabled={busy}>Save service</button></form>
    </section><section><h2>Machine resources</h2>
      <form onSubmit={e=>submit(e,'notes')}>{notesFields.map(([key,label])=><label key={key}>{label}<input name={key} defaultValue={notes[key] || ''}/></label>)}<button disabled={busy}>Save operating notes</button></form>
      {data.manuals.map(m=><p key={m.kind}><button onClick={()=>getManual(m)}>{m.name}</button> Â· {m.kind} manual Â· {m.editor}</p>)}
      <form onSubmit={e=>submit(e,'manuals')}><label>Manual type<select name="kind"><option>user</option><option>parts</option><option>error-code</option></select></label><label>Relevant manual extract and page (optional)<textarea name="excerpt" maxLength={1000}/></label><label>PDF (up to 5 MB)<input required type="file" accept="application/pdf" name="file"/></label><button disabled={busy}>Save manual</button></form>
    </section><section><h2>Forecast checks</h2>{data.forecasts.map(f=><p key={f.issued}>{time(f.issued)} Â· Predicted crossing: {f.predicted?'Yes':'No'} Â· {f.result}</p>)}</section>
    <section><h2>Ask about this machine</h2><form onSubmit={e=>submit(e,'guidance')}><label>Question<input name="question" required minLength={2} maxLength={500}/></label><button disabled={busy}>Check machine records</button></form>{reply && <p>{reply.answer} {reply.sources.join(' · ')}</p>}</section>
    <section><h2>Resource edit history</h2>{data.edits.map((e,i)=><p key={i}>{time(e.edited)} Â· {e.resource} Â· {e.editor}</p>)}</section></>}
    <p role="status">{message}</p>
  </main>
}

