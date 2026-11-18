import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import StatusBadge from '../ui/StatusBadge'

function MachineCard({ machine }) {
  return (
    <Link
      to={`/machines/${machine.categoryId}/${machine.id}`}
      className="group flex flex-col overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="flex-1 space-y-3 p-5">
        <div className="flex items-start justify-between gap-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{machine.type}</p>
          <StatusBadge status={machine.status} />
        </div>
        <p className="text-sm leading-relaxed text-slate-600">{machine.brief}</p>
      </div>

      <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50 px-5 py-3">
        <span className="font-semibold text-navy-900">{machine.name}</span>
        <ChevronRight size={18} className="text-slate-400 transition group-hover:translate-x-1 group-hover:text-teal-600" />
      </div>
    </Link>
  )
}

export default MachineCard
