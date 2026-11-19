import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import RecordForm, { Field } from '../components/RecordForm'

export default function Machines() {
  const { registry: { categories, engineers, machines }, request } = useOutletContext()
  const [editing, setEditing] = useState(null)
  const current = editing || {}
  function save(body) {
    body.category_id = Number(body.category_id)
    body.engineer_id = body.engineer_id ? Number(body.engineer_id) : null
    return request('/admin/registry/machines' + (editing ? '/' + editing.id : ''), { method: editing ? 'PUT' : 'POST', body })
  }
  return <><h1>Machine registry</h1>
    <RecordForm title="Add category" save={body => request('/admin/registry/categories', { method:'POST', body })}><Field label="Category name" name="name" /></RecordForm>
    <RecordForm key={current.id || 'new'} title={editing ? 'Edit machine' : 'Register machine'} save={save} onSaved={() => setEditing(null)}>
      {[['machine_id','Machine ID'],['name','Machine name'],['model','Model'],['serial_number','Serial number'],['location','Location']].map(([name,label]) => <Field key={name} name={name} label={label} defaultValue={current[name] || ''} />)}
      <Field name="category_id" label="Category" choices={categories} defaultValue={current.category_id || ''} />
      <Field name="status" label="Recorded status" choices={['Working','Maintenance','Stopped'].map(name => ({id:name,name}))} defaultValue={current.status || 'Stopped'} />
      <Field name="engineer_id" label="Assigned engineer (optional)" choices={engineers} required={false} defaultValue={current.engineer_id || ''} />
      {editing && <button type="button" onClick={() => setEditing(null)}>Cancel edit</button>}
    </RecordForm>
    <section><h2>Registered machines</h2>{machines.map(m => <p key={m.id}>{m.name} · {m.machine_id} · {m.category_name} · {m.location} · {m.status} · {m.engineer_name || 'Unassigned'} <button onClick={() => setEditing(m)}>Edit</button></p>)}{!machines.length && <p>No machines registered.</p>}</section>
  </>
}
