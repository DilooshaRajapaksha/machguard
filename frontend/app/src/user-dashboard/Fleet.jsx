import FleetOverview from './FleetOverview'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiRequest } from '../services/api'

import MachineTile, { typePicture } from '../components/MachineTile'

export default function Fleet({ overview = false }) {
  const { typeId } = useParams()
  const { token } = useAuth()
  const [machines, setMachines] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    let timer
    async function load() {
      try {
        const rows = await apiRequest('/equipment', { token, signal: controller.signal })
        if (!controller.signal.aborted) {
          setMachines(rows.map(machine => ({
            ...machine,
            category_id: machine.category_id ?? 'uncategorized',
            category_name: typeof machine.category_name === 'string' && machine.category_name.trim()
              ? machine.category_name.trim() : 'Uncategorized',
          })))
          setError('')
        }
      } catch (problem) {
        if (!controller.signal.aborted) setError(problem.message)
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(load, 5000)
      }
    }
    load()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [token])

  if (error) return <p role="alert">{error}</p>
  if (!machines) return <p role="status">Loading machines...</p>
  if (overview) return <FleetOverview machines={machines} />
  const groups = new Map()
  for (const machine of machines) {
    const id = String(machine.category_id)
    if (!groups.has(id)) groups.set(id, [])
    groups.get(id).push(machine)
  }
  const rows = typeId ? groups.get(typeId) || [] : machines
  const title = typeId ? rows[0]?.category_name || 'Machine type' : 'Machine types'

  return <section className="space-y-5">
    {typeId && <Link to="/machines" className="underline">All machine types</Link>}
    <h1 className="text-3xl font-semibold">{title}</h1>
    {!rows.length && <p>No machines registered{typeId ? ' for this type' : ''}.</p>}
    {typeId ? <div className="grid gap-3 md:grid-cols-2">
      {rows.map(machine => <MachineTile key={machine.machine_id} machine={machine} />)}
    </div> : <div className="grid gap-3 md:grid-cols-2">
      {[...groups].map(([id, items]) => <Link className="fleet-tile block rounded-xl border border-slate-200 bg-white p-4 machine-picture type-picture" key={id} to={'/machines/type/'+id}>
        <img alt="" src={typePicture(items[0].category_name)} /><strong>{items[0].category_name}</strong><p>{items.length} {items.length === 1 ? 'machine' : 'machines'}</p>
      </Link>)}
    </div>}
  </section>
}
