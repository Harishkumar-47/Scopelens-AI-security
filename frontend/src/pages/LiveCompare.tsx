import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, CheckCircle2, ShieldCheck, ShieldOff } from 'lucide-react'
import LiveGraph from '../components/LiveGraph'
import { api } from '../services/api'
import type { LiveComparison } from '../types'

export default function LiveCompare() {
  const [result, setResult] = useState<LiveComparison | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.liveCompare().then(setResult).catch(cause => setError(cause instanceof Error ? cause.message : 'Comparison failed')) }, [])
  return <section className="page live-compare-page"><div className="compare-intro"><div className="eyebrow">BEFORE & AFTER</div><h1>Same AI. Same job. <em>Different protection.</em></h1><p>Both sides run the same safe demo. The only change is whether ScopeLens protects the AI's tools.</p></div>{error && <div className="error">{error}</div>}{result ? <><div className="live-compare-grid"><article className="comparison-card vulnerable"><div className="comparison-kicker"><ShieldOff size={20}/> PROTECTION OFF</div><h2>Demo password exposed</h2><p>A fake instruction in the project issue led AI to open a fake password and send it to a local demo receiver.</p><LiveGraph graph={result.before.graph} compact/><div className="comparison-outcome danger"><strong>DEMO DATA EXPOSED</strong><span>Fake data only · nothing sent to the Internet</span></div></article><article className="comparison-card protected"><div className="comparison-kicker"><ShieldCheck size={20}/> PROTECTION ON</div><h2>Dangerous action blocked</h2><p>ScopeLens stopped the password read before it happened. AI could still read the project and finish its job.</p><LiveGraph graph={result.after.graph} compact/><div className="comparison-outcome safe"><strong>THE PROJECT TASK STILL WORKS</strong><span>No demo password was opened</span></div></article></div><div className="compare-outcome live-outcome"><CheckCircle2 size={24}/><div><strong>AI can do its job without access to everything.</strong><p>Same task and same Demo AI on both sides. All files are fake.</p></div><Link to="/live" className="button secondary">Try it live <ArrowRight size={16}/></Link></div></> : !error && <div className="panel loading-panel">Running the safe comparison…</div>}</section>
}
