import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/auth/ProtectedRoute'
import Layout from './components/layout/Layout'
import Login from './user-dashboard/Login'
import Dashboard from './user-dashboard/Dashboard'
import Machines from './user-dashboard/Machines'
import BenchHistory from './user-dashboard/BenchHistory'
import MachineCategory from './user-dashboard/MachineCategory'
import Support from './user-dashboard/Support'
import Assistant from './user-dashboard/Assistant'
import NotFound from './user-dashboard/NotFound'

import Equipment from './user-dashboard/Equipment'
import AdminLayout from './admin-dashboard/AdminLayout'
import AdminHome from './admin-dashboard/pages/Home'
import AdminMachines from './admin-dashboard/pages/Machines'
import AdminEngineers from './admin-dashboard/pages/Engineers'
import AdminReports from './admin-dashboard/pages/Reports'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminHome />} />
            <Route path="machines" element={<AdminMachines />} />
            <Route path="engineers" element={<AdminEngineers />} />
            <Route path="reports" element={<AdminReports />} />
          </Route>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />

            <Route path="/equipment/:code" element={<Equipment />} />
            <Route path="/machines" element={<Machines />} />
            <Route path="/machines/test-bench/motor-1" element={<BenchHistory />} />

            <Route
              path="/machines/:categoryId"
              element={<MachineCategory />}
            />

            <Route
              path="/machines/:categoryId/:machineId"
              element={<MachineCategory />}
            />

            <Route path="/support" element={<Support />} />

            <Route path="/assistant" element={<Assistant />} />

            <Route path="*" element={<NotFound />} />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
  )
}

export default App
