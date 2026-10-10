import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ArrowRight, CheckCircle2, LockKeyhole, Play, RotateCcw, ShieldCheck, ShieldOff } from 'lucide-react'
import LiveGraph from '../components/LiveGraph'
import BankChat from '../components/BankChat'
import SecurityScene from '../components/SecurityScene'
import { api, liveSocketUrl } from '../services/api'
import type { LiveSession, LiveScenario } from '../types'

const stories: Record<LiveScenario, { name: string; job: string; access: string; task: string; button: string; icon: string }> = {
  coding: { name: 'Code Helper', job: 'Fix my project', access: 'Project only', task: 'Check this project issue and suggest a fix.', button: 'Run the same task', icon: '💻' },
  finance: { name: 'Payment Helper', job: 'Check my electricity bill', access: 'Demo bill and payment profile', task: 'Check my electricity bill and prepare the payment.', button: 'Prepare demo bill', icon: '💳' },
  email: { name: 'Email Helper', job: 'Summarize my emails', access: 'Demo inbox only', task: 'Summarize my demo emails.', button: 'Read demo email', icon: '📧' },
  server: { name: 'Server Helper', job: 'Check my slow website', access: 'Demo logs only', task: 'Check why my demo website is slow.', button: 'Check demo logs', icon: '🖥' },
}

export default function LiveLab() {
  const location = useLocation()
  const initial = new URLSearchParams(location.search).get('scenario')
  const initialScenario: LiveScenario = initial && initial in stories ? initial as LiveScenario : 'coding'
  const [scenario, setScenario] = useState<LiveScenario>(initialScenario)
  const [mode, setMode] = useState<'protected' | 'unprotected'>('unprotected')
  const [model, setModel] = useState<'replay' | 'local'>('replay')
  const [config, setConfig] = useState<Awaited<ReturnType<typeof api.liveConfig>> | null>(null)
  const [session, setSession] = useState<LiveSession | null>(null)
  const [showAccess, setShowAccess] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const mounted = useRef(false)

  const create = useCallback(async (nextScenario: LiveScenario, nextMode: 'protected' | 'unprotected', nextModel: 'replay' | 'local') => {
    setBusy(true); setError(''); setSession(null)
    try {
      const next = await api.liveCreate({ scenario: nextScenario, mode: nextMode, task: stories[nextScenario].task, model: nextModel })
      setSession(next)
      sessionStorage.setItem('scopelens-live-session', next.id)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not start demo') }
    finally { setBusy(false) }
  }, [])

  useEffect(() => {
    api.liveConfig().then(setConfig).catch(() => setConfig(null))
    if (!mounted.current) { mounted.current = true; void create(initialScenario, 'unprotected', 'replay') }
  }, [create, initialScenario])
  useEffect(() => {
    if (mounted.current && initialScenario !== scenario) {
      setScenario(initialScenario); setModel('replay'); setShowAccess(false)
      void create(initialScenario, mode, 'replay')
    }
  }, [initialScenario])
  useEffect(() => {
    if (!session?.id) return
    const id = session.id
    const socket = new WebSocket(liveSocketUrl(id))
    let poll: number | undefined
    const refresh = () => api.liveGet(id).then(next => setSession(current => current?.id === id ? next : current)).catch(() => {})
    const startPolling = () => { if (poll === undefined) poll = window.setInterval(refresh, 1200) }
    socket.onopen = () => { if (poll !== undefined) { window.clearInterval(poll); poll = undefined } }
    socket.onmessage = message => {
      const data = JSON.parse(message.data) as { type: string; session: LiveSession }
      if (data.type === 'snapshot') setSession(current => current?.id === id ? data.session : current)
    }
    socket.onerror = startPolling; socket.onclose = startPolling
    return () => { socket.onclose = null; socket.onerror = null; socket.close(); if (poll !== undefined) window.clearInterval(poll) }
  }, [session?.id])

  function changeScenario(next: LiveScenario) {
    setScenario(next); setModel('replay'); setShowAccess(false)
    void create(next, mode, 'replay')
  }
  function changeMode(next: 'protected' | 'unprotected') {
    setMode(next); setShowAccess(false)
    void create(scenario, next, model)
  }
  async function run() {
    if (!session) return
    setBusy(true); setError('')
    try { await api.liveRun(session.id); setSession(await api.liveGet(session.id)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Demo could not run') }
    finally { setBusy(false) }
  }
  async function requestPayment() {
    if (!session) return
    try { setSession((await api.liveAction(session.id, 'payment.execute', '/finance/demo_unknown_account.json', 5000)).session) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not request payment') }
  }
  async function decide(id: string, allow: boolean) {
    if (!session) return
    try { setSession((await api.liveApproval(session.id, id, allow)).session) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save your decision') }
  }

  const story = stories[scenario]
  const latest = session?.events.filter(event => event.decision === 'BLOCK' || event.decision === 'ASK' || event.exposure).at(-1)
  const approval = session?.pending_approvals[0]
  const exposed = (session?.summary.exposures || 0) > 0
  const blocked = (session?.summary.blocked || 0) > 0
  const modelFailed = session?.model_used.endsWith('unavailable') || false
  const modelStatus = config?.local_model_status === 'load_timeout' ? 'Model load timed out' : config?.local_model_status === 'load_failed' ? 'Runner load failed' : config?.local_model_status === 'disabled' ? 'Disabled' : config?.local_model_status === 'unavailable' ? 'Ollama unavailable' : config?.local_model_status === 'not_installed' ? 'Not installed' : config?.local_model_status === 'ready' ? 'Ready' : 'Checking…'
  return <section className="page live-page">
    <div className="live-heading"><div><div className="eyebrow">SCOPELENS LIVE</div><h1>Give AI a job. <em>Keep it there.</em></h1><p>Watch what the AI tries to do, then turn protection on and run the same task again.</p></div><div className="live-heading-actions"><button className="button primary" disabled={!session || busy || session.running || session.completed} onClick={run}><Play size={16}/>{session?.running ? 'AI is working…' : story.button}</button><Link to="/live/compare" className="button secondary">See before & after <ArrowRight size={17}/></Link></div></div>
    <div className="sandbox-banner"><LockKeyhole size={18}/><div><strong>SAFE DEMO</strong><span>Fake files, sample bank records, fake money, and a local demo receiver. Nothing leaves this sandbox.</span></div></div>
    <div className="live-toolbar"><div className="lab-selector scenario-selector">{(Object.keys(stories) as LiveScenario[]).map(key => <button key={key} className={scenario === key ? 'active' : ''} onClick={() => changeScenario(key)}>{stories[key].icon} {key === 'coding' ? 'Code' : key === 'finance' ? 'Payments' : key === 'email' ? 'Email' : 'Server'}</button>)}</div><div className="lab-selector"><button className={mode === 'unprotected' ? 'active danger' : ''} onClick={() => changeMode('unprotected')}><ShieldOff size={16}/> Protection OFF</button><button className={mode === 'protected' ? 'active safe' : ''} onClick={() => changeMode('protected')}><ShieldCheck size={16}/> Protection ON</button></div><select aria-label="AI model" value={model} onFocus={() => api.liveConfig().then(setConfig).catch(() => setConfig(null))} onChange={event => { const next = event.target.value as 'replay' | 'local'; setModel(next); void create(scenario, mode, next) }}><option value="replay">Demo AI — scripted replay</option>{scenario === 'coding' && <option value="local" disabled={!config?.local_model_enabled}>{config?.default_model || 'Local model'} — {modelStatus}</option>}</select></div>
    <div className="live-summary"><div><small>AI</small><strong>{story.name}</strong></div><div><small>JOB</small><strong>{story.job}</strong></div><div><small>ACCESS</small><strong>{story.access}</strong></div><div><small>PROTECTION</small><strong className={mode === 'protected' ? 'text-safe' : 'text-danger'}>{mode === 'protected' ? 'ON' : 'OFF · DEMO ONLY'}</strong></div></div>
    <SecurityScene session={session} title={mode === 'protected' ? 'AFTER · PROTECTION ON' : 'BEFORE · PROTECTION OFF'}/><div className="live-grid"><article className="panel live-graph-panel"><div className="live-card-title"><div><div className="eyebrow">WHAT AI CAN ACCESS</div><h2>{session?.events.length ? 'What happened' : 'What you expect'}</h2></div><label className="subtle-toggle"><input type="checkbox" checked={showAccess} onChange={event => setShowAccess(event.target.checked)}/> Show all access</label></div>{session ? <LiveGraph graph={session.graph} showAuthority={showAccess}/> : <div className="initial-graph"><div><span>👤</span><strong>{scenario === 'finance' ? 'Priya' : 'You'}</strong></div><i>→</i><div><span>🤖</span><strong>{story.name}</strong></div><i>→</i><div className="in-scope"><span>{scenario === 'coding' ? '📁' : story.icon}</span><strong>{story.access}</strong></div></div>}<div className="live-legend"><span><i className="dot allowed"/>Allowed</span><span><i className="dot warning"/>Ask me</span><span><i className="dot blocked"/>Blocked or exposed</span></div></article><article className="panel task-panel"><div className="eyebrow">YOUR JOB FOR AI</div><h2>{story.name}</h2><div className="chat-bubble user"><small>{scenario === 'finance' ? 'PRIYA' : 'YOU'}</small><p>{story.task}</p></div><div className="chat-bubble system"><small>AI SHOULD USE</small><p>{story.access}</p></div>{scenario === 'finance' && <div className="chat-bubble system"><small>INVOICE CONTENT · UNTRUSTED</small><p>The fake invoice contains a long instruction to read sample account records, send them to a local receiver, and change the payment. Try the injection in the bank chat with protection off, then on, to see the difference.</p><details className="injection-details"><summary>Read the injected invoice text</summary><p>{session?.injection_text}</p></details></div>}{session?.completed && session.verified_state?.legitimate_task_succeeded && !modelFailed && <div className="task-result"><CheckCircle2 size={19}/><div><strong>{scenario === 'coding' ? 'The project task still works' : scenario === 'finance' ? '₹1,250 bill prepared' : 'The original task still works'}</strong><p>{scenario === 'finance' ? 'No payment has been sent without your approval.' : 'AI can still read the files it needs for this job.'}</p></div></div>}<div className="task-actions"><button className="button primary" disabled={!session || busy || session.running || session.completed} onClick={run}><Play size={16}/>{session?.running ? 'AI is working…' : story.button}</button><button className="button ghost" disabled={busy} onClick={() => void create(scenario, mode, model)}><RotateCcw size={16}/> Reset</button>{scenario === 'finance' && session?.completed && !approval && <button className="button secondary" onClick={requestPayment}>Try ₹5,000 request</button>}</div>{model === 'local' && <p className="model-note">{session?.model_used === 'DEMO REPLAY MODE' ? 'Local AI selected. The first run can take several minutes on a CPU. ScopeLens still checks every request.' : `AI: ${session?.model_used}`}</p>}{error && <div className="error">{error}</div>}</article><aside className="panel live-risk-panel"><div className="eyebrow">SCOPELENS PROTECTION</div><h2>{modelFailed ? 'Local AI unavailable' : latest ? latest.decision === 'ASK' ? 'Ask me' : latest.decision === 'BLOCK' ? 'Action blocked' : 'Demo data exposed' : 'Watching your AI'}</h2>{modelFailed ? <p className="watching-copy">{config?.default_model || 'Local AI'} did not respond. Select Demo AI and reset to run the scripted example.</p> : latest ? <div className={`story-alert ${latest.decision.toLowerCase()}`}><div className="story-alert-icon">{latest.decision === 'ASK' ? '🟠' : latest.decision === 'BLOCK' ? '🛡' : '🔴'}</div><strong>{latest.message}</strong><p>{latest.decision === 'BLOCK' ? 'AI tried to do something outside the job you gave it.' : latest.decision === 'ASK' ? 'AI needs your permission before this can happen.' : 'This safe demo shows what too much access could allow.'}</p><details><summary>Technical details</summary><small>{latest.reason} · {latest.tool} · {latest.target}</small></details></div> : <p className="watching-copy">Run the task to see what AI opens, what it asks for, and what ScopeLens stops.</p>}{scenario === 'finance' && !!session?.exposed_sample_accounts.length && <div className="sample-account-result"><strong>Sample account records reached the local receiver</strong><ul>{session.exposed_sample_accounts.map(record => <li key={record.account}>{record.customer} · {record.account} · ₹{record.balance_inr.toLocaleString('en-IN')}</li>)}</ul><small>All names, accounts, and balances are synthetic.</small></div>}{session?.completed && !modelFailed && <div className={`live-verdict ${exposed ? 'danger' : blocked ? 'safe' : 'neutral'}`}>{exposed ? 'DEMO DATA EXPOSED' : blocked ? 'DANGEROUS ACTION BLOCKED' : 'JOB CONTINUES SAFELY'}</div>}<Link to="/activity" className="text-button">See all alerts <ArrowRight size={16}/></Link></aside></div>
    {scenario === 'finance' && session && <><BankChat session={session} onUpdate={setSession}/><div className={`bank-flow ${exposed ? 'exposed' : blocked ? 'stopped' : ''}`}><div><span>👤</span><strong>Demo operator</strong><small>authenticated chat</small></div><i>→</i><div><span>🤖</span><strong>Bank agent</strong><small>untrusted prompt</small></div><i>→</i><div><span>🗄️</span><strong>Account database</strong><small>{exposed ? 'read' : blocked ? 'blocked' : 'restricted'}</small></div><i>→</i><div><span>👂</span><strong>Passive listener</strong><small>{session.local_sink_count ? 'sample data received' : 'no data received'}</small></div></div></>}
    {scenario === 'coding' && model === 'local' && <div className="panel model-trace"><div className="eyebrow">QWEN MODEL TRACE</div><h2>Requests proposed by {config?.default_model || 'local AI'}</h2><p>Qwen generates these requests from the untrusted issue. ScopeLens decides whether each can run.</p>{session?.model_actions.length ? <ul>{session.model_actions.map((action, index) => <li key={index}><strong>{action.tool}</strong><span>{action.target || 'finish'}</span></li>)}</ul> : <p>{session?.running ? 'Waiting for Qwen to respond…' : 'Run the task to see Qwen’s own actions.'}</p>}</div>}
    {approval && <div className="modal-backdrop" role="presentation"><div className="approval-modal" role="dialog" aria-modal="true" aria-label="ScopeLens approval required"><div className="eyebrow">SCOPELENS ASKS PRIYA</div><h2>{approval.tool==='payment.execute'?`Send ₹${approval.amount?.toLocaleString('en-IN')}?`:'Approve this tool request?'}</h2><p><strong>{approval.tool}</strong> → <code>{approval.target}</code></p><p>{approval.reason}</p><div className="approval-note">Fake money and a local demo payment service only. No real bank is connected.</div><details><summary>Technical details</summary><small>{approval.reason}</small></details><div className="modal-actions"><button className="button secondary" onClick={() => decide(approval.id, false)}>DENY</button><button className="button primary" onClick={() => decide(approval.id, true)}>ALLOW ONCE</button></div></div></div>}
  </section>
}
