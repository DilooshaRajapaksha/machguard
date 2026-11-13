import { Link } from 'react-router-dom'
import { ArrowRight, Gauge, Zap } from 'lucide-react'
import { countByStatus, getMachinesByCategory } from '../../data/machines'
import { statuses } from '../../data/statuses'

const icons = {
  compressors: Gauge,
  generators: Zap,
}

function CategoryCard({ category }) {
  const Icon = icons[category.id] ?? Gauge
  const categoryMachines = getMachinesByCategory(category.id)
  const counts = countByStatus(categoryMachines)

  return (
    <Link
      to={`/machines/${category.id}`}
      className="group flex flex-col overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-1 hover:shadow-lg"
    >
      <div className="relative flex h-40 items-center justify-center overflow-hidden bg-linear-to-br from-navy-800 via-navy-700 to-teal-700">
        <div className="absolute -bottom-10 -left-10 h-40 w-40 rounded-full bg-white/5" />
        <div className="absolute -right-6 -top-12 h-36 w-36 rounded-full bg-teal-300/10" />
        <Icon size={64} strokeWidth={1.5} className="relative text-teal-200 transition group-hover:scale-110" />
      </div>

      <div className="flex flex-1 flex-col p-5">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-navy-900">{category.name}</h3>
          <span className="text-sm text-slate-500">{categoryMachines.length} units</span>
        </div>
        <p className="mt-1 text-sm text-slate-600">{category.description}</p>

        <div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-600">
          {Object.entries(counts).map(([status, count]) => (
            <span key={status} className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${statuses[status].dot}`} />
              {count} {statuses[status].label.toLowerCase()}
            </span>
          ))}
        </div>

        <span className="mt-5 flex items-center gap-1 text-sm font-semibold text-teal-700">
          View {category.name.toLowerCase()}
          <ArrowRight size={16} className="transition group-hover:translate-x-1" />
        </span>
      </div>
    </Link>
  )
}

export default CategoryCard