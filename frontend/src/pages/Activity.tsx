import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { api } from '../services/api'
import type { LiveEvent, LiveSession } from '../types'

function title(event: LiveEvent) {
  if (event.tool === 'payment.execute') return '💳 Payment'
  if (event.classification === 'FINANCIAL') return '💳 Payment'
  if (event.tool === 'server.delete') return '🖥 Server Change'
  if (event.tool === 'demo_send') return '📤 Data Send'
  if (event.classification === 'SECRET') return '🔑 Password Access'
  if (event.classification === 'SENSITIVE') return '📄 Private File'
  if (event.untrusted_source) return '📄 Untrusted Content'
  return '📁 File Access'
}
function status(event: LiveEvent) {
  return event.decision === 'ASK' ? 'WAITING FOR YOU' : event.decision === 'BLOCK' ? 'BLOCKED' : event.exposure ? 'DEMO EXPOSED' : event.decision === 'ALLOW' ? 'ALLOWED' : 'NOTICED'
}
export default function Activity() {
  const [sessions, setSessions] = useState<LiveSession[]>([])
  useEffect(() => { const refresh = () => api.liveList().then(setSessions).catch(() => setSessions([])); refresh(); const timer = window.setInterval(refresh, 2000); return () => window.clearInterval(timer) }, [])
  const events = sessions.flatMap(session => session.events.map(event => ({ ...event, agent: session.agent_name, mode: session.mode }))).sort((a, b) => b.at.localeCompare(a.at))
  return <section className="page activity-page"><div className="page-title"><div><div className="eyebrow">SCOPELENS ALERTS</div><h1>What AI tried to do.</h1><p>Every alert comes from a real decision in the local demo. Files, money, and accounts here are fake.</p></div><Link to="/live" className="button primary">Open Live <ArrowRight size={16}/></Link></div><div className="alert-feed">{events.length ? events.slice(0, 70).map(event => <article className={`panel alert-feed-item ${event.exposure ? 'exposure' : event.decision.toLowerCase()}`} key={event.id}><div className="alert-feed-top"><strong>{title(event)}</strong><span className={`status-chip ${event.exposure ? 'exposure' : event.decision.toLowerCase()}`}>{status(event)}</span></div><p>{event.message}</p><small>{event.agent} · {new Date(event.at).toLocaleTimeString()}</small><details><summary>Technical details</summary><code>{event.tool || 'observation'} · {event.target}</code><p>{event.reason}</p></details></article>) : <div className="panel empty-timeline">No alerts yet. Run one of the safe demos in Live.</div>}</div></section>
}
