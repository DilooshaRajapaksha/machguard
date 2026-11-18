import { NavLink } from 'react-router-dom'
import { statuses } from '../../data/statuses'

function MachineSidebar({ category, machines }) {
  return (
    <aside className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200 lg:sticky lg:top-24 lg:self-start">
      <NavLink to={`/machines/${category.id}`} end className="block bg-navy-900 px-4 py-3 text-white">
        <h2 className="font-semibold">{category.name}</h2>
        <p className="text-xs text-slate-400">{machines.length} units</p>
      </NavLink>

      <nav className="flex gap-2 overflow-x-auto p-3 lg:flex-col lg:gap-1">
        {machines.map((machine) => (
          <NavLink
            key={machine.id}
            to={`/machines/${category.id}/${machine.id}`}
            className={({ isActive }) =>
              `flex shrink-0 items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive ? 'bg-teal-50 text-teal-800' : 'text-slate-600 hover:bg-slate-50 hover:text-navy-900'
              }`
            }
          >
            <span className={`h-2 w-2 rounded-full ${statuses[machine.status].dot}`} />
            {machine.name}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

export default MachineSidebar