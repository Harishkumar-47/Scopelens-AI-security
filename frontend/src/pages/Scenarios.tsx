import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Headset, ServerCog, WalletCards } from 'lucide-react'
import { api } from '../services/api'
import type { Agent } from '../types'
const icons = [Headset, ServerCog, WalletCards]
export default function Scenarios() {
  const [items, setItems] = useState<(Agent & { id: string })[]>([])
  const navigate = useNavigate()
  useEffect(() => { api.scenarios().then(setItems).catch(() => setItems([])) }, [])
  return <section className="page"><div className="eyebrow">GUIDED DEMOS</div><h1>Explore a real permission chain.</h1><p className="lead">Choose a sample agent, inspect its permissions, and run the analysis yourself. All scenarios use demo data.</p><div className="scenario-grid">{items.map((agent, i) => { const Icon = icons[i] || Headset; return <article className="scenario-card" key={agent.id}><div className="scenario-icon"><Icon size={27}/></div><div className="scenario-number">SCENARIO 0{i + 1}</div><h2>{agent.name}</h2><p>{agent.purpose}</p><div className="permission-tags">{agent.permissions.slice(0, 4).map(p => <span key={p}>{p}</span>)}{agent.permissions.length > 4 && <span>+{agent.permissions.length - 4}</span>}</div><button className="text-button" onClick={() => navigate('/new', { state: { agent } })}>Open scenario <ArrowRight size={17}/></button></article> })}</div></section>
}
