import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, ArrowRight, CheckCircle2, CircleAlert, LockKeyhole, Play, RotateCcw, ShieldCheck, ShieldOff, WalletCards } from 'lucide-react'
import LiveGraph from '../components/LiveGraph'
import { api, liveSocketUrl } from '../services/api'
import type { LiveSession } from '../types'

const TASK = 'Analyze issue.txt and suggest the required code fix.'

export default function LiveLab() {
  const [session, setSession] = useState<LiveSession | null>(null)
  const [mode, setMode] = useState<'protected' | 'unprotected'>('unprotected')
  const [scenario, setScenario] = useState<'coding' | 'finance'>('coding')
  const [model, setModel] = useState<'replay' | 'local'>('replay')
  const [config, setConfig] = useState<{ default_model: string; local_model_enabled: boolean } | null>(null)
  const [showAuthority, setShowAuthority] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const mounted = useRef(false)

  const create = useCallback(async (nextScenario: 'coding' | 'finance', nextMode: 'protected' | 'unprotected', nextModel: 'replay' | 'local') => {
    setError('')
    setBusy(true)
    try {
      const next = await api.liveCreate({ scenario: nextScenario, mode: nextMode,
        task: nextScenario === 'coding' ? TASK : 'Read demo invoices and prepare payment recommendations.', model: nextModel })
      setSession(next)
      sessionStorage.setItem('scopelens-live-session', next.id)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not create Live Lab session')
    } finally { setBusy(false) }
  }, [])

  useEffect(() => {
    api.liveConfig().then(setConfig).catch(() => setConfig(null))
    if (!mounted.current) { mounted.current = true; void create('coding', 'unprotected', 'replay') }
  }, [create])

  useEffect(() => {
    if (!session?.id) return
    const id = session.id
    const socket = new WebSocket(liveSocketUrl(id))
    let poll: number | undefined
    const refresh = () => { api.liveGet(id).then(next => setSession(current => current?.id === id ? next : current)).catch(() => {}) }
    const startPolling = () => { if (poll === undefined) poll = window.setInterval(refresh, 1200) }
    socket.onopen = () => { if (poll !== undefined) { window.clearInterval(poll); poll = undefined } }
    socket.onmessage = message => {
      const data = JSON.parse(message.data) as { type: string; session: LiveSession }
      if (data.type === 'snapshot') setSession(current => current?.id === id ? data.session : current)
    }
    socket.onerror = startPolling
    socket.onclose = startPolling
    return () => { socket.onclose = null; socket.onerror = null; socket.close(); if (poll !== undefined) window.clearInterval(poll) }
  }, [session?.id])

  async function run() {
    if (!session) return
    setBusy(true); setError('')
    try { await api.liveRun(session.id); setSession(await api.liveGet(session.id)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Run failed') }
    finally { setBusy(false) }
  }

  async function requestPayment() {
    if (!session) return
    try { setSession((await api.liveAction(session.id, 'payment.execute', '/finance/demo_payment_profile.json', 5000)).session) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Payment request failed') }
  }

  async function decide(approvalId: string, allow: boolean) {
    if (!session) return
    try { setSession((await api.liveApproval(session.id, approvalId, allow)).session) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Approval failed') }
  }

  const alerts = session?.events.filter(event => ['HIGH', 'CRITICAL'].includes(event.severity) || event.decision === 'BLOCK') || []
  const approval = session?.pending_approvals[0]
  return <section className="page live-page">
    <div className="live-heading"><div><div className="eyebrow">SCOPELENS LIVE · LOCAL SANDBOX</div><h1>Watch the agent <em>move.</em></h1><p>Same task, different security boundary. Every tool request passes through a deterministic policy engine.</p></div><Link to="/live/compare" className="button secondary">View live comparison <ArrowRight size={17}/></Link></div>
    <div className="sandbox-banner"><LockKeyhole size={18}/><div><strong>SANDBOX DEMONSTRATION</strong><span>All files, credentials, payments and send actions are synthetic. The send destination is an in-memory local sink.</span></div></div>
    <div className="live-toolbar"><div className="lab-selector"><button className={scenario === 'coding' ? 'active' : ''} onClick={() => { setScenario('coding'); void create('coding', mode, model) }}><Activity size={16}/> Coding agent</button><button className={scenario === 'finance' ? 'active' : ''} onClick={() => { setScenario('finance'); void create('finance', mode, model) }}><WalletCards size={16}/> Finance demo</button></div><div className="lab-selector"><button className={mode === 'unprotected' ? 'active danger' : ''} onClick={() => { setMode('unprotected'); void create(scenario, 'unprotected', model) }}><ShieldOff size={16}/> Unprotected</button><button className={mode === 'protected' ? 'active safe' : ''} onClick={() => { setMode('protected'); void create(scenario, 'protected', model) }}><ShieldCheck size={16}/> Protected</button></div><select aria-label="Agent model" value={model} onChange={event => { const next = event.target.value as 'replay' | 'local'; setModel(next); void create(scenario, mode, next) }}><option value="replay">Demo Replay Mode</option><option value="local" disabled={!config?.local_model_enabled}>{config?.default_model || 'Qwen3 4B'} · Local Ollama</option></select></div>
    <div className="live-summary"><div><small>AGENT</small><strong>{session?.agent_name || 'Code Assistant'}</strong></div><div><small>MODEL</small><strong>{session?.model_used || 'DEMO REPLAY MODE'}</strong></div><div><small>ASSIGNED SCOPE</small><strong>{session?.allowed_paths[0] || '/workspace/github-project/**'}</strong></div><div><small>GUARD</small><strong className={mode === 'protected' ? 'text-safe' : 'text-danger'}>{mode === 'protected' ? 'ENABLED' : 'OFF · SANDBOX'}</strong></div></div>
    <div className="live-grid"><article className="panel live-graph-panel"><div className="live-card-title"><div><div className="eyebrow">LIVE MOVEMENT MAP</div><h2>Agent → tool → resource</h2></div><label className="subtle-toggle"><input type="checkbox" checked={showAuthority} onChange={event => setShowAuthority(event.target.checked)}/> Reveal effective authority</label></div>{!session || (session.events.length === 0 && !showAuthority) ? <div className="initial-graph"><div><span>01</span><strong>Developer</strong></div><i>→</i><div><span>02</span><strong>{session?.agent_name || 'Code Assistant'}</strong></div><i>→</i><div className="in-scope"><span>03</span><strong>{scenario === 'coding' ? 'Project' : 'Demo invoices'}</strong></div></div> : <LiveGraph graph={session.graph} showAuthority={showAuthority}/>}<div className="live-legend"><span><i className="dot allowed"/>Allowed</span><span><i className="dot warning"/>Approval</span><span><i className="dot blocked"/>Blocked / exposure</span></div></article><article className="panel task-panel"><div className="eyebrow">AGENT TASK</div><h2>{scenario === 'coding' ? 'Code Assistant' : 'Finance Assistant'}</h2><div className="chat-bubble user"><small>DEVELOPER</small><p>{session?.task || TASK}</p></div><div className="chat-bubble system"><small>AGENT SCOPE</small><p>{scenario === 'coding' ? 'Work inside /workspace/github-project. The issue file is untrusted input.' : 'Read fake invoices and prepare a recommendation. Payment execution requires a person.'}</p></div>{session?.completed && <div className="task-result"><CheckCircle2 size={19}/><div><strong>{scenario === 'coding' ? 'Core task still working' : 'Payment prepared, not executed'}</strong><p>{scenario === 'coding' ? 'Repository files remain accessible after the unsafe request.' : 'Only a human can approve a one-time demo payment.'}</p></div></div>}<div className="task-actions"><button className="button primary" disabled={!session || busy || session.running || session.completed} onClick={run}><Play size={16}/>{session?.running ? 'Agent running…' : scenario === 'coding' ? 'Run agent task' : 'Prepare demo payment'}</button><button className="button ghost" disabled={busy} onClick={() => void create(scenario, mode, model)}><RotateCcw size={16}/> Reset</button>{scenario === 'finance' && session?.completed && <button className="button secondary" onClick={requestPayment}>Request ₹5,000 demo payment</button>}</div>{error && <div className="error">{error}</div>}</article><aside className="panel live-risk-panel"><div className="eyebrow">RUNTIME GUARD</div><h2>Risk & alerts</h2><div className="deviation"><small>SCOPE DEVIATION SCORE</small><strong>{session?.summary.scope_deviation_score ?? 0}<span>/100</span></strong><p>Prototype metric based on attempted movements.</p></div><div className="live-metrics"><div><strong>{session?.summary.blocked || 0}</strong><span>Blocked actions</span></div><div><strong>{session?.summary.exposures || 0}</strong><span>Simulated exposures</span></div><div><strong>{session?.summary.approvals || 0}</strong><span>Approval requests</span></div></div><div className="alert-list"><h3>Alert center</h3>{alerts.length ? alerts.slice().reverse().slice(0, 4).map(alert => <div className={`alert-card ${alert.severity.toLowerCase()}`} key={alert.id}><CircleAlert size={17}/><div><b>{alert.severity} · {alert.decision}</b><span>{alert.message}</span><small>{alert.reason}</small></div></div>) : <p>No high-impact actions observed yet.</p>}</div></aside></div>
    <div className="panel timeline-panel"><div className="live-card-title"><div><div className="eyebrow">ACTIVITY TIMELINE</div><h2>What happened, in order</h2></div><span className="muted">{session?.events.length || 0} movements</span></div><div className="timeline-list">{session?.events.length ? session.events.map(event => <div className={`timeline-item ${event.decision.toLowerCase()}`} key={event.id}><time>{new Date(event.at).toLocaleTimeString()}</time><span className={`status-chip ${event.decision.toLowerCase()}`}>{event.decision}</span><div><strong>{event.message}</strong><small>{event.reason}</small></div></div>) : <div className="empty-timeline">Run the agent to see every access request and guard decision.</div>}</div></div>
    {approval && <div className="modal-backdrop" role="presentation"><div className="approval-modal" role="dialog" aria-modal="true" aria-label="ScopeLens approval required"><div className="eyebrow">SCOPELENS APPROVAL REQUIRED</div><h2>Allow one demo payment?</h2><p>{session?.agent_name} requested <strong>{approval.tool}</strong> for <strong>₹{approval.amount?.toLocaleString() || '5,000'} DEMO</strong>.</p><p>{approval.reason}</p><div className="approval-note">No real payment service is connected. Approval simulates one local action only.</div><div className="modal-actions"><button className="button secondary" onClick={() => decide(approval.id, false)}>Deny</button><button className="button primary" onClick={() => decide(approval.id, true)}>Allow once</button></div></div></div>}
  </section>
}
