import { Activity, CalendarClock, Cpu, MapPin, Wrench } from 'lucide-react'
import StatusBadge from '../ui/StatusBadge'

function formatDate(value) {
  return new Date(value).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function MachineDetails({ machine }) {
  const info = [
    { label: 'Type', value: machine.type, icon: Wrench },
    { label: 'Controller', value: machine.controller, icon: Cpu },
    { label: 'Location', value: machine.location, icon: MapPin },
    { label: 'Last service', value: formatDate(machine.lastService), icon: CalendarClock },
  ]

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-bold text-navy-900">{machine.name}</h1>
          <StatusBadge status={machine.status} />
        </div>
        <p className="mt-3 text-slate-600">{machine.brief}</p>

        <dl className="mt-6 grid gap-4 sm:grid-cols-2">
          {info.map(({ label, value, icon: Icon }) => (
            <div key={label} className="flex items-center gap-3 rounded-xl bg-slate-50 p-4">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-white text-teal-600 ring-1 ring-slate-200">
                <Icon size={18} />
              </span>
              <div>
                <dt className="text-xs text-slate-500">{label}</dt>
                <dd className="font-medium text-navy-900">{value}</dd>
              </div>
            </div>
          ))}
        </dl>
      </div>

      <div className="flex items-start gap-4 rounded-2xl border border-dashed border-slate-300 bg-white/60 p-6">
        <Activity size={22} className="mt-0.5 shrink-0 text-slate-400" />
        <div>
          <h2 className="font-semibold text-navy-900">Live readings</h2>
          <p className="mt-1 text-sm text-slate-500">
            Sensor data and fault guidance for this machine will show here once it is connected to the backend.
          </p>
        </div>
      </div>
    </div>
  )
}

export default MachineDetails