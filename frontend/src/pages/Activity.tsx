import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity as ActivityIcon, ArrowRight } from 'lucide-react'
import { api } from '../services/api'
import type { LiveSession } from '../types'

export default function Activity() {
  const [sessions, setSessions] = useState<LiveSession[]>([])
  useEffect(() => { const refresh = () => api.liveList().then(setSessions).catch(() => setSessions([])); refresh(); const timer = window.setInterval(refresh, 2000); return () => window.clearInterval(timer) }, [])
  const events = sessions.flatMap(session => session.events.map(event => ({ ...event, agent: session.agent_name, mode: session.mode }))).sort((a, b) => b.at.localeCompare(a.at))
  return <section className="page activity-page"><div className="page-title"><div><div className="eyebrow">RUNTIME VISIBILITY</div><h1>Activity, not assumptions.</h1><p>Agent movements from the current local demo process. No real accounts or external destinations.</p></div><Link to="/live" className="button primary">Open Live Agent Lab <ArrowRight size={16}/></Link></div><div className="activity-stats"><div><strong>{sessions.length}</strong><span>Demo sessions</span></div><div><strong>{sessions.reduce((sum, session) => sum + session.summary.blocked, 0)}</strong><span>Blocked actions</span></div><div><strong>{sessions.reduce((sum, session) => sum + session.summary.approvals, 0)}</strong><span>Approval requests</span></div></div><div className="panel activity-table"><div className="live-card-title"><div><div className="eyebrow">RECENT EVENTS</div><h2>Agent movement log</h2></div><ActivityIcon size={22}/></div>{events.length ? events.slice(0, 60).map(event => <div className="activity-row" key={event.id}><time>{new Date(event.at).toLocaleTimeString()}</time><span className={`status-chip ${event.decision.toLowerCase()}`}>{event.decision}</span><div><strong>{event.message}</strong><small>{event.agent} · {event.mode} · {event.target}</small></div><span className={`risk-severity ${event.severity.toLowerCase()}`}>{event.severity}</span></div>) : <div className="empty-timeline">No runtime events yet. Start a sandbox demo in the Live Agent Lab.</div>}</div></section>
}
