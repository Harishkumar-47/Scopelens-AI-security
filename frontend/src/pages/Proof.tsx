import { useEffect, useState } from 'react'

type Evidence = {id:string;at:string;agent:string;tool:string;target:string;decision:string;reason:string;source:string;rule:string;execution?:{executed:boolean;after:{receiver_count:number;payment_count:number;server_deleted:boolean;legitimate_task_succeeded:boolean}}}
export default function Proof() {
  const [events,setEvents]=useState<Evidence[]>([])
  const [error,setError]=useState('')
  const refresh=()=>fetch('/api/gateway/proof').then(async r=>{if(!r.ok)throw new Error('Evidence unavailable');return r.json()}).then(r=>setEvents(r.events)).catch(e=>setError(String(e)))
  useEffect(()=>{void refresh()},[])
  const download=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({redacted:true,events},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='scopelens-proof.json';a.click();URL.revokeObjectURL(url)}
  return <section className="page"><div className="eyebrow">PERSISTENT BACKEND EVIDENCE</div><h1>Proof of each tool decision.</h1><p>Execution state comes from the synthetic sandbox. Raw prompts and file contents are excluded from the persistent report.</p><button className="button secondary" onClick={()=>void refresh()}>Refresh</button> <button className="button primary" onClick={download}>Download redacted JSON</button>{error&&<p role="alert">{error}</p>}{!events.length&&<div className="panel"><p>Run a Live or Tester scenario, or the Python gateway example, to create evidence.</p></div>}{events.map(e=><details className="panel" key={e.id}><summary><strong>{e.decision}</strong> · {e.agent} · {e.tool||'workflow'} · {e.at}</summary><p>{e.target}</p><p>{e.rule}: {e.reason}</p><p>Instruction source: {e.source}</p>{e.execution&&<p>Executed: {String(e.execution.executed)} · Receiver deliveries: {e.execution.after.receiver_count} · Payments: {e.execution.after.payment_count} · Server deleted: {String(e.execution.after.server_deleted)} · Legitimate access continued: {String(e.execution.after.legitimate_task_succeeded)}</p>}</details>)}</section>
}
