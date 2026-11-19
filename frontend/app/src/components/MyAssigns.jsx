import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { apiRequest } from '../services/api'

export default function MyAssigns() {
  const { token } = useAuth()
  const [machines, setMachines] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()

    async function loadMachines() {
      setMachines(null)
      setError('')

      try {
        const result = await apiRequest('/engineer/me', {
          token,
          signal: controller.signal,
        })

        if (!controller.signal.aborted) {
          setMachines(result.machines)
        }
      } catch (problem) {
        if (!controller.signal.aborted) {
          setError(problem.message)
        }
      }
    }

    loadMachines()
    return () => controller.abort()
  }, [token])

  if (error) return <p role="alert">{error}</p>
  if (machines === null) return <p role="status">Loading your assignments…</p>
  if (machines.length === 0) {
    return <p>Your administrator hasn’t assigned a machine to you yet.</p>
  }

  return (
    <section aria-label="My assigned machines" className="grid gap-4 md:grid-cols-2">
      {machines.map(machine => (
        <article
          key={machine.machine_id}
          className="rounded-md border border-slate-200 bg-white p-5"
        >
          <p className="text-sm text-slate-500">{machine.machine_id}</p>
          <h2 className="mt-1 text-lg font-semibold">{machine.name}</h2>
          <p className="mt-2 text-sm">{machine.category_name} · {machine.location}</p>
          <p className="mt-1 text-sm">Recorded status: {machine.status}</p>
        </article>
      ))}
    </section>
  )
}