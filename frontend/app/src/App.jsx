import MachineAlerts from './components/MachineAlerts'
import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/auth/ProtectedRoute'
import Layout from './components/layout/Layout'
import Login from './user-dashboard/Login'
import Dashboard from './user-dashboard/Dashboard'
import BenchHistory from './user-dashboard/BenchHistory'
import Support from './user-dashboard/Support'
import Assistant from './user-dashboard/Assistant'
import NotFound from './user-dashboard/NotFound'

import Equipment from './user-dashboard/Equipment'
import Fleet from './user-dashboard/Fleet'
import MyAssigns from './components/MyAssigns'
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
            <Route path="support" element={<Support admin />} />
            <Route path="notifications" element={<MachineAlerts />} />
            <Route path="reports" element={<AdminReports />} />
          </Route>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />

            <Route path="/equipment/:code" element={<Equipment />} />
            <Route path="/machines" element={<Fleet />} />
            <Route path="/machines/type/:typeId" element={<Fleet />} />
            <Route path="/my-assigns" element={<MyAssigns />} />
            <Route path="/equipment/:code/history" element={<BenchHistory />} />

            <Route path="/notifications" element={<MachineAlerts />} />
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
