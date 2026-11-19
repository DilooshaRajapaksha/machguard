import { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import RecordForm, { Field } from '../components/RecordForm'

export default function Engineers() {
  const { registry: { engineers, machines }, request } = useOutletContext()
  const [users, setUsers] = useState([])
  const [error, setError] = useState('')
  const unlinked = engineers.filter(e => !e.user_id)
  const linkedIds = new Set(engineers.map(e => e.user_id))
  const available = users.filter(u => u.is_active && u.role === 'viewer' && !linkedIds.has(u.id))
    .map(u => ({id:u.id, name:u.full_name + ' (' + u.username + ')'}))
  useEffect(() => {
    let active = true
    request('/admin/users').then(result => { if (active) { setUsers(result); setError('') } })
      .catch(problem => { if (active) setError(problem.message) })
    return () => { active = false }
  }, [request, engineers])
  return <><h1>Engineering team</h1><div className="forms">
    <RecordForm title="Add engineer" save={body => request('/admin/registry/engineers', {method:'POST',body})}>
      <Field name="name" label="Full name" /><Field name="email" type="email" label="Email address" /><Field name="specialty" label="Specialty" />
    </RecordForm>
    <RecordForm title="Create engineer login" save={body => request('/admin/users', {method:'POST',body:{...body,role:'viewer'}})}>
      <Field name="full_name" label="Full name" /><Field name="username" label="Username" minLength={3} maxLength={32} />
      <Field name="password" label="Temporary password" type="password" autoComplete="new-password" minLength={10} />
    </RecordForm>
    </div>{error && <p role="alert">{error}</p>}
    {unlinked.length > 0 && available.length > 0 && <RecordForm title="Link an engineer to a login" save={body => request('/admin/registry/engineers/' + body.engineer_id + '/account', {method:'PUT', body:{user_id:Number(body.user_id)}})}>
      <Field label="Engineer" name="engineer_id" choices={unlinked} /><Field label="Login" name="user_id" choices={available} />
    </RecordForm>}
    <section><h2>Engineer assignments</h2>{engineers.map(e => <article key={e.id}><h3>{e.name}</h3><p>{e.email} · {e.specialty}</p><p>Login: {e.login_username || 'Awaiting link'}</p><p>Machines: {machines.filter(m => m.engineer_id === e.id).map(m => m.name).join(', ') || 'Unassigned'}</p></article>)}{!engineers.length && <p>No engineers registered.</p>}</section></>
}
