import { Link } from 'react-router-dom'
const scenarios = [
  { id: 'coding', icon: '💻', name: 'Code', description: 'AI fixes a project issue. A fake instruction tries to make it read a demo password.' },
  { id: 'finance', icon: '💳', name: 'Payments', description: 'AI checks a ₹1,250 bill. A fake invoice asks it to send ₹5,000 instead.' },
  { id: 'email', icon: '📧', name: 'Email', description: 'AI summarizes email. An untrusted message tries to send private data.' },
  { id: 'server', icon: '🖥', name: 'Server', description: 'AI checks website logs. A fake log line asks it to delete server settings.' },
]
export default function Scenarios() {
  return <section className="page"><div className="eyebrow">FOUR SAFE DEMOS</div><h1>Pick a story.</h1><p className="lead">Each demo uses fake data and shows what ScopeLens allows, asks about, or blocks.</p><div className="scenario-grid">{scenarios.map(item => <article className="scenario-card simple-scenario" key={item.id}><div className="scenario-icon">{item.icon}</div><h2>{item.name}</h2><p>{item.description}</p><Link className="text-button" to={`/live?scenario=${item.id}`}>Try it in Live →</Link></article>)}</div></section>
}
