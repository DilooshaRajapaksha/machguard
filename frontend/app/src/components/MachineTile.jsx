import { Link } from 'react-router-dom'

const card = 'fleet-tile block rounded-xl border border-slate-200 bg-white p-4'

export function typePicture(name = '') {
  const type = String(name || '').toLowerCase()
  if (type.includes('compressor')) return '/compressor.jpg'
  if (type.includes('generator')) return '/generator.jpg'
  if (type.includes('motor')) return '/fleet-2.jpg'
  return '/fleet-0.jpg'
}

export default function MachineTile({ machine }) {
  return <Link className={card + ' machine-picture asset-card'} to={'/equipment/' + encodeURIComponent(machine.machine_id)}>
    <img alt="" src={typePicture(machine.category_name)} />
    <span className="asset-status" data-state={machine.status}>{machine.status}</span>
    <strong>{machine.name}</strong>
    <p>{[machine.machine_id, machine.location].filter(Boolean).join(' / ')}</p>
    <p className="asset-health">Temperature health &middot; {machine.probe_health || 'Unknown'}</p>
  </Link>
}
