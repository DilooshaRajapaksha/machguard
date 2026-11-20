import Fleet from './Fleet'
import MachineAlerts from '../components/MachineAlerts'

export default function Dashboard() {
  return <div className="dashboard-home">
    <Fleet overview />
    <MachineAlerts preview />
  </div>
}
