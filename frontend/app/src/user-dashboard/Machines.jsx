import PageHeader from '../components/ui/PageHeader'
import CategoryCard from '../components/machines/CategoryCard'
import { categories } from '../data/machines'
import { appName } from '../config'

function Machines() {
  return (
    <div>
      <PageHeader title="Machines" subtitle={`All the equipment ${appName} is watching.`} />
      <div className="grid gap-6 sm:grid-cols-2">
        {categories.map((category) => (
          <CategoryCard key={category.id} category={category} />
        ))}
      </div>
    </div>
  )
}

export default Machines