import { useOutletContext } from 'react-router-dom'
import RecordForm, { Field } from '../components/RecordForm'

export default function Reports() {
  const { registry: { machines, reports }, request } = useOutletContext()
  return <><h1>Maintenance reports</h1>{machines.length ? <RecordForm title="Create report" save={body => request('/admin/registry/reports', {method:'POST', body:{...body, machine_id:Number(body.machine_id)}})}>
    <Field label="Machine" name="machine_id" choices={machines} /><Field label="Report title" name="title" minLength={3} />
    <label>Maintenance notes<textarea name="notes" required minLength={3} maxLength={5000} /></label>
  </RecordForm> : <p>Register a machine to create its first report.</p>}
  <section><h2>Saved reports</h2>{reports.map(r => <article key={r.id}><h3>{r.title}</h3><small>{r.machine_name} · {r.created_by} · {new Date(r.created_at).toLocaleString()}</small><p>{r.notes}</p></article>)}{!reports.length && <p>No reports yet.</p>}</section></>
}
