import MachineTile from './MachineTile'
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
    <section className="space-y-5">
      <h1 className="text-3xl font-semibold">My Assigns</h1>
      <div className="grid gap-3 md:grid-cols-2">
        {machines.map(machine => <MachineTile key={machine.machine_id} machine={machine} />)}
      </div>
    </section>
  )
}
