import { Link, Navigate, useParams } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import MachineSidebar from '../components/machines/MachineSidebar'
import MachineCard from '../components/machines/MachineCard'
import MachineDetails from '../components/machines/MachineDetails'
import { getCategory, getMachinesByCategory } from '../data/machines'
import NotFound from './NotFound'

function MachineCategory() {
  const { categoryId, machineId } = useParams()
  const category = getCategory(categoryId)

  if (!category) return <NotFound />

  const categoryMachines = getMachinesByCategory(categoryId)
  const selectedMachine = categoryMachines.find((machine) => machine.id === machineId)

  if (machineId && !selectedMachine) {
    return <Navigate to={`/machines/${categoryId}`} replace />
  }

  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-1 text-sm text-slate-500">
        <Link to="/machines" className="hover:text-teal-700">
          Machines
        </Link>
        <ChevronRight size={14} />
        <Link to={`/machines/${category.id}`} className="hover:text-teal-700">
          {category.name}
        </Link>
        {selectedMachine && (
          <>
            <ChevronRight size={14} />
            <span className="font-medium text-navy-900">{selectedMachine.name}</span>
          </>
        )}
      </nav>

      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <MachineSidebar category={category} machines={categoryMachines} />

        {selectedMachine ? (
          <MachineDetails machine={selectedMachine} />
        ) : (
          <div className="grid content-start gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {categoryMachines.map((machine) => (
              <MachineCard key={machine.id} machine={machine} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default MachineCategory
