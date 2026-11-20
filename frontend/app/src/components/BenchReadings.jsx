import SensorChart from './SensorChart'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest } from '../services/api'
import { useAuth } from '../context/AuthContext'

const fields = [
  ['probe_c', 'Surface probe 1', '°C'], ['probe2_c', 'Surface probe 2', '°C'],
  ['air_c', 'DHT11 air temperature (unverified)', '°C'], ['humidity_pct', 'DHT11 humidity (unverified)', '%'],
  ['current_a', 'Motor current (uncalibrated)', 'A'], ['motor_v', 'Motor voltage (uncalibrated)', 'V'],
  ['vibration_rms', 'Acceleration variation RMS', 'm/s²'], ['sample_hz', 'Sampling rate', 'Hz'],
  ['current_adc_v', 'Current sensor ADC', 'V'], ['voltage_adc_v', 'Voltage sensor ADC', 'V'],
  ['timing_resets', 'Sampling timing resets', ''], ['uptime_s', 'Board uptime', 's'],
  ['ax', 'Acceleration X', 'm/s²'], ['ay', 'Acceleration Y', 'm/s²'], ['az', 'Acceleration Z', 'm/s²'],
]

export default function BenchReadings({ machineId = '', showHistory = true }) {
  const { token, user } = useAuth()
  const query = machineId ? '?machine_id=' + encodeURIComponent(machineId) : ''
  const [rows, setRows] = useState([])
  const sample = rows.at(-1)
  const [status, setStatus] = useState('Checking ESP32 readings…')
  useEffect(() => {
    const controller = new AbortController()
    setRows([])
    setStatus("Checking ESP32 readings.")
    let timer
    let loadHistory = showHistory
    async function poll() {
      try {
        if (loadHistory) {
          loadHistory = false
          const history = await apiRequest('/bench/history' + query, { token, signal: controller.signal })
          if (controller.signal.aborted) return
          setRows(history.reverse())
        }
        const data = await apiRequest('/bench/latest' + query, { token, signal: controller.signal })
        if (controller.signal.aborted) return
        setRows(previous => {
          if (!data) return []
          if (previous.at(-1)?.received_at === data.received_at) return previous
          const cutoff = Date.parse(data.received_at) - 300000
          return [...previous.filter(row => Date.parse(row.received_at) >= cutoff), data]
        })
        setStatus(!data ? 'Waiting for the first ESP32 reading.' :
          Date.now() - Date.parse(data.received_at) > 15000 ? 'Last saved reading · no recent update' : 'Receiving readings')
      } catch (error) {
        if (!controller.signal.aborted) setStatus(error.message)
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(poll, 3000)
      }
    }
    poll()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [token, query, showHistory])
  return <section className="rounded-md border border-slate-200 bg-white p-5">
    <h2 className="text-xl font-semibold">Live ESP32 readings</h2>
    {showHistory && (machineId || user.role === "admin") && <Link className="text-sm text-teal-700 underline" to={'/equipment/' + encodeURIComponent(machineId) + '/history'}>View five-minute history</Link>}
    <p className="text-sm text-slate-600">{status}</p>
    {sample && <><p className="mt-2 text-sm">Received {new Date(sample.received_at).toLocaleString()}</p></>}
      <div className="sensor-grid">{fields.map((field,index) =>
        <SensorChart key={field[0]} field={field} index={index} rows={rows} />)}</div>
  </section>
}
