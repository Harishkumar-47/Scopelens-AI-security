import { useRef, useState } from 'react'
import type { LiveSession } from '../types'

export default function SecurityScene({ session, title }: { session?: LiveSession | null; title?: string }) {
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null)
  const [selected, setSelected] = useState('')
  const protectedMode = session?.mode === 'protected'
  const events = session?.events || []
  const blocked = events.some(e => e.decision === 'BLOCK')
  const asking = !!session?.pending_approvals.length
  const exposed = events.some(e => e.exposure)
  const acted = !!session?.demo_payments.length || !!session?.demo_deleted
  const danger = exposed || acted
  const outcome = asking ? 'APPROVAL REQUIRED' : blocked ? 'ACCESS BLOCKED' : danger ? acted && !exposed ? 'DEMO ACTION EXECUTED' : 'DATA EXPOSED' : events.length ? 'ALLOWED WORK CONTINUES' : 'READY TO TEST'
  const resource = session?.scenario === 'finance' ? ['🏦', 'Bank data'] : session?.scenario === 'email' ? ['📬', 'Private email'] : session?.scenario === 'server' ? ['🖥️', 'Server settings'] : ['🔑', 'Demo passwords']
  const nodes = [['👤', 'User', 'Your request starts the agent’s task.'], ['🤖', session?.agent_name || 'AI Agent', session?.model_used || 'Select an installed model or Demo AI.'], ['📄', 'Untrusted content', 'A prompt, project file, email or log can carry manipulative instructions.'], ...(protectedMode ? [['🛡️', 'ScopeLens', 'Backend policy evaluates the tool request independently of the model.']] : []), [resource[0], resource[1], blocked ? 'The gateway denied this request before reading or modifying the resource.' : asking ? 'Execution waits for a one-time human decision.' : 'Only fixed synthetic sandbox resources are available.'], ['📤', 'Demo receiver', `${session?.local_sink_count || 0} in-memory deliveries. No external network transfer.`]]
  return <div className={`security-scene ${danger ? 'scene-danger' : blocked ? 'scene-safe' : asking ? 'scene-warn' : ''}`}>
    <div className="scene-top"><span>{title || 'FOLLOW THE TOOL REQUEST'}</span><div className="scene-controls"><button aria-label="Zoom out" onClick={() => setZoom(z => Math.max(.55, z-.15))}>−</button><button aria-label="Reset map view" onClick={() => { setZoom(1); setPan({x:0,y:0}) }}>Fit</button><button aria-label="Zoom in" onClick={() => setZoom(z => Math.min(1.8,z+.15))}>+</button></div></div>
    <div className="scene-viewport" onPointerDown={e => { if ((e.target as HTMLElement).closest('button')) return; drag.current={x:e.clientX,y:e.clientY,px:pan.x,py:pan.y}; e.currentTarget.setPointerCapture(e.pointerId) }} onPointerMove={e => { if (drag.current) setPan({x:drag.current.px+e.clientX-drag.current.x,y:drag.current.py+e.clientY-drag.current.y}) }} onPointerUp={() => { drag.current=null }} onPointerCancel={() => { drag.current=null }}>
      <div className="scene-plane" style={{transform:`translate(${pan.x}px, ${pan.y}px) scale(${zoom})`}}>{nodes.map((node,i) => <div className="scene-step" key={node[1]}>{i>0 && <span className={`scene-wire ${events.length && !(protectedMode && (blocked || asking) && i >= nodes.length-2) ? 'moving' : ''} ${protectedMode && i === nodes.length-2 && (blocked || asking) ? 'wire-stop' : ''}`}>{protectedMode && i === nodes.length-2 && blocked ? '✕' : protectedMode && i === nodes.length-2 && asking ? '⏸' : '→'}</span>}<button className={`iso-card ${node[1] === 'ScopeLens' ? 'shield-card' : ''} ${protectedMode && (blocked || asking) && i >= nodes.length-2 ? 'unreached' : ''} ${selected === node[2] ? 'selected' : ''}`} onClick={() => setSelected(node[2])}><span className="iso-icon">{node[0]}</span><strong>{node[1]}</strong><small>{i === 0 ? 'REQUEST' : node[1] === 'ScopeLens' ? 'POLICY BOUNDARY' : 'SANDBOX'}</small></button></div>)}</div>
    </div><div className="scene-bottom"><strong role="status">{outcome}</strong><span>{selected || 'Click a card to inspect · drag to pan · use + / − to zoom'}</span></div>
    {session?.verified_state?.legitimate_task_succeeded && <div className="continuation-path">🤖 AI <span>→</span> 📁 Allowed work <span>→</span> ✅ CONTINUES</div>}
  </div>
}
