import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiRequest } from '../services/api'

export default function BenchHistory() {
  const { token } = useAuth()
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    let timer
    async function refresh() {
      try {
        const result = await apiRequest('/bench/history', { token, signal: controller.signal })
        if (controller.signal.aborted) return
        setRows(result)
        setError('')
      } catch (failure) {
        if (!controller.signal.aborted) setError(failure.message)
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(refresh, 5000)
      }
    }
    refresh()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [token])

  return <section className="mx-auto max-w-5xl space-y-4 p-5">
    <Link to="/" className="text-teal-700 underline">Dashboard</Link>
    <h1 className="text-2xl font-semibold">ESP32 Test Motor 1</h1>
    <p>USB readings from the last five minutes, newest first.</p>
    {error && <p role="alert">{error}</p>}
    {!error && !rows && <p>Loading history…</p>}
    {!error && rows?.length === 0 && <p>No USB readings in the last five minutes.</p>}
    {!!rows?.length && <div className="overflow-auto rounded border bg-white"><table className="w-full text-left text-sm">
      <thead><tr>{['Time', 'Probe 1 (°C)', 'Probe 2 (°C)', 'Vibration RMS (m/s²)'].map(label =>
        <th key={label} className="p-3">{label}</th>)}</tr></thead>
      <tbody>{rows.map((row, index) => <tr key={row.received_at + index} className="border-t">
        <td className="p-3">{new Date(row.received_at).toLocaleTimeString()}</td>
        {[row.probe_c, row.probe2_c, row.vibration_rms].map((value, column) =>
          <td key={column} className="p-3">{value ?? 'Unavailable'}</td>)}
      </tr>)}</tbody>
    </table></div>}
  </section>
}
