const colors = ['#027e81','#474bb0','#a44520','#2466a0','#953d70','#6755a4']

export default function SensorChart({ rows, field, index }) {
  const [key, label, unit] = field
  const values = rows.map(row => row[key]).filter(Number.isFinite)
  const current = rows.at(-1)?.[key]
  const clock = stamp => new Date(stamp).toLocaleTimeString()
  const start = Date.parse(rows[0]?.received_at)
  const end = Date.parse(rows.at(-1)?.received_at)
  const low = Math.min(...values)
  const high = Math.max(...values)
  let previous
  let path = ''
  const points = []
  for (const row of rows) {
    const stamp = Date.parse(row.received_at)
    const value = row[key]
    if (!Number.isFinite(value)) { previous = null; continue }
    const x = 5 + 270 * (stamp-start)/Math.max(1,end-start)
    const y = high === low ? 38 : 70 - 64*(value-low)/(high-low)
    path += (previous != null && stamp-previous <= 15000 ? ' L' : ' M') + x + ' ' + y
    previous = stamp
    points.push({ x, y, time: row.received_at, value })
  }
  return <article className="sensor-chart" style={{'--signal': colors[index % colors.length]}}>
    <h3>{label}</h3><strong>{Number.isFinite(current) ? current + ' ' + unit : rows.length ? 'Unavailable' : 'Awaiting data'}</strong>
    {values.length > 0 ? <>
      <p>{low}–{high} {unit}</p>
      <svg viewBox="0 0 280 78" role="img" aria-label={label+' over time'}>
        {[8,38,69].map(y => <line key={y} x1="0" x2="280" y1={y} y2={y} stroke="#dce7eb" strokeDasharray="3 4"/>)}
        {points.map(p => <line key={p.time} x1={p.x} x2={p.x} y1={p.y} y2="74" stroke="var(--signal)" opacity=".14" strokeWidth="4" />)}
        <path d={path} stroke="var(--signal)" strokeWidth="2.4" strokeLinejoin="round" strokeLinecap="round" fill="none" />
        {points.map(p => <circle key={p.time} cx={p.x} cy={p.y} r="2.2" fill="var(--signal)"><title>{clock(p.time)} · {p.value} {unit}</title></circle>)}
      </svg>
      <footer><time>{clock(start)}</time><time>{clock(end)}</time></footer>
    </> : <div className="chart-empty" aria-hidden="true" />}
  </article>
}
