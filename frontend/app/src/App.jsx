import { Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import Machines from './pages/Machines'
import MachineCategory from './pages/MachineCategory'
import Support from './pages/Support'
import Assistant from './pages/Assistant'
import NotFound from './pages/NotFound'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/machines" element={<Machines />} />
        <Route path="/machines/:categoryId" element={<MachineCategory />} />
        <Route path="/machines/:categoryId/:machineId" element={<MachineCategory />} />
        <Route path="/support" element={<Support />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default App