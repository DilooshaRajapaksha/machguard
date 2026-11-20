import { Link, useOutletContext } from 'react-router-dom'

export default function Home() {
  const { registry: { machines, reports } } = useOutletContext()
  return <><h1>Dockyard overview</h1><section className="metrics">
    <Link to="machines"><strong>{machines.filter(m => m.status === 'Working').length}</strong>Machines recorded as working</Link>
    <Link to="engineers"><strong>{new Set(machines.map(m => m.engineer_id).filter(Boolean)).size}</strong>Engineers with assignments</Link>
    <Link to="reports"><strong>{reports.length}</strong>Maintenance reports</Link>
  </section><section><h2>Recently registered machines</h2>{machines.length ? machines.slice(0,5).map(m => <p className="registry-row" key={m.id}><Link to={'/equipment/' + encodeURIComponent(m.machine_id)}>{m.name}</Link> · {m.location} · {m.status}</p>) : <p>No machines registered.</p>}<Link to="machines">Open machine registry</Link></section></>
}
