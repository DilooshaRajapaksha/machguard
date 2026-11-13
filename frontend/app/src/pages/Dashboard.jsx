import { Activity, CircleCheck, CircleStop, TriangleAlert } from 'lucide-react'
import CategoryCard from '../components/machines/CategoryCard'
import { categories, countByStatus, machines } from '../data/machines'
import { currentUser } from '../data/user'
import { companyName } from '../config'

function getGreeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

function Dashboard() {
  const firstName = currentUser.name.split(' ')[0]
  const counts = countByStatus(machines)

  const stats = [
    { label: 'Total machines', value: machines.length, icon: Activity, color: 'bg-slate-100 text-navy-700' },
    { label: 'Running', value: counts.running, icon: CircleCheck, color: 'bg-emerald-50 text-emerald-600' },
    { label: 'Needs attention', value: counts.warning, icon: TriangleAlert, color: 'bg-amber-50 text-amber-600' },
    { label: 'Stopped', value: counts.stopped, icon: CircleStop, color: 'bg-rose-50 text-rose-600' },
  ]

  return (
    <div className="space-y-10">
      <section className="relative overflow-hidden rounded-3xl bg-navy-900 px-6 py-8 text-white sm:px-10 sm:py-10">
        <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-teal-400/20 blur-3xl" />
        <div className="absolute -bottom-20 right-24 h-48 w-48 rounded-full bg-sky-500/10 blur-3xl" />
        <div className="relative">
          <p className="text-sm font-medium text-teal-300">
            {getGreeting()}, {firstName}
          </p>
          <h1 className="mt-2 text-2xl font-bold sm:text-3xl">Dockyard maintenance guidance</h1>
          <p className="mt-3 max-w-2xl text-slate-300">
            This is the {companyName} maintenance guidance prototype. Pick a machine type below to check
            the status of each unit.
          </p>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${color}`}>
              <Icon size={20} />
            </span>
            <p className="mt-4 text-3xl font-bold text-navy-900">{value}</p>
            <p className="text-sm text-slate-500">{label}</p>
          </div>
        ))}
      </section>

      <section>
        <div className="mb-5">
          <h2 className="text-xl font-bold text-navy-900">Machines</h2>
          <p className="text-sm text-slate-500">Choose a machine type to see every unit.</p>
        </div>
        <div className="grid gap-6 sm:grid-cols-2">
          {categories.map((category) => (
            <CategoryCard key={category.id} category={category} />
          ))}
        </div>
      </section>
    </div>
  )
}

export default Dashboard