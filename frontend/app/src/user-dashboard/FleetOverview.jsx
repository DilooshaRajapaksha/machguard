import './fleet-overview.css'

const statuses = [
  { label: 'Working', status: 'Working', color: '#007767' },
  { label: 'Stopped', status: 'Stopped', color: '#526479' },
  { label: 'Under maintenance', status: 'Maintenance', color: '#966018' },
]

export default function FleetOverview({ machines }) {
  const total = machines.length
  const groups = statuses.map(item => ({
    ...item, count: machines.filter(machine => machine.status === item.status).length,
  }))
  return <section className="fleet-overview">
    <h1>Fleet overview</h1>
    <div className="fleet-photos">
      {[{ label: 'Total machines', count: total }, ...groups].map((item, i) =>
        <article className="fleet-photo" key={item.label} style={{backgroundImage: 'url(/fleet-' + i + '.jpg)'}}>
          <div><h2>{item.label}</h2><strong>{item.count}</strong></div>
        </article>)}
    </div>
    <h2 className="fleet-graph-heading">Share of registered machines</h2>
    <div className="fleet-graphs">
      {groups.map(item => {
        const percent = total ? Math.round(100 * item.count / total) : 0
        return <article key={item.status}>
          <h3>{item.label}</h3>
          <div className="fleet-share" style={{'--share': percent + '%', '--segment': item.color}} aria-label={percent + '%'}>{percent}%</div>
          <p>{total ? item.count + ' of ' + total + ' ' + (total === 1 ? 'machine' : 'machines') : 'No registered machines'}</p>
          <div className="fleet-bar" aria-hidden="true"><span style={{width: percent + '%', background: item.color}} /></div>
        </article>
      })}
    </div>
  </section>
}
