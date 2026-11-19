import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/auth/ProtectedRoute'
import Layout from './components/layout/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Machines from './pages/Machines'
import BenchHistory from './pages/BenchHistory'
import MachineCategory from './pages/MachineCategory'
import Support from './pages/Support'
import Assistant from './pages/Assistant'
import NotFound from './pages/NotFound'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />

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
