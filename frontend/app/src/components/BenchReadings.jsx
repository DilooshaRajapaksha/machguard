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

export default function BenchReadings({ machineId = '' }) {
  const { token, user } = useAuth()
  const query = machineId ? '?machine_id=' + encodeURIComponent(machineId) : ''
  const [sample, setSample] = useState(null)
  const [status, setStatus] = useState('Checking USB readings…')
  useEffect(() => {
    const controller = new AbortController()
    let timer
    async function poll() {
      try {
        const data = await apiRequest('/bench/latest' + query, { token, signal: controller.signal })
        if (controller.signal.aborted) return
        setSample(data)
        setStatus(!data ? 'Waiting for the first USB reading.' :
          Date.now() - Date.parse(data.received_at) > 15000 ? 'Last saved reading · no recent update' : 'Receiving readings')
      } catch (error) {
        if (!controller.signal.aborted) setStatus(error.message)
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(poll, 3000)
      }
    }
    poll()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [token, query])
  return <section className="rounded-md border border-slate-200 bg-white p-5">
    <h2 className="text-xl font-semibold">ESP32 test bench</h2>
    {(machineId || user.role === "admin") && <Link className="text-sm text-teal-700 underline" to={'/machines/test-bench/motor-1' + query}>View five-minute history</Link>}
    <p className="text-sm text-slate-600">{status}</p>
    {sample && <><p className="mt-2 text-sm">Received {new Date(sample.received_at).toLocaleString()}</p>
      <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">{fields.filter(([key]) => sample.uptime_s == null || !['ax', 'ay', 'az'].includes(key)).map(([key, label, unit]) =>
        <div key={key}><dt className="text-sm text-slate-500">{label}</dt><dd>{sample[key] == null ? 'Unavailable' : sample[key] + ' ' + unit}</dd></div>)}</dl></>}
  </section>
}
