import type { Agent, AnalysisResult, SimulationResult, LiveSession, LiveComparison, LiveScenario, PracticalSession } from '../types'
const ownerTokens = new Map<string, string>()
async function call<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { signal: AbortSignal.timeout(300000), ...options, headers: { 'Content-Type': 'application/json', ...options?.headers } })
  if (!response.ok) {
    const body = await response.text()
    let message = body
    try { const parsed = JSON.parse(body); if (typeof parsed.detail === 'string') message = parsed.detail } catch { /* Keep a plain-text server error. */ }
    throw new Error(message.slice(0, 300))
  }
  const data = await response.json()
  if (data.id && data.owner_token) ownerTokens.set(data.id, data.owner_token)
  return data as T
}
export const api = {
  testerModels: () => call<{models:{id:string;label:string}[];ollama_available:boolean;recommended_model:string}>('/tester/models'),
  testerCreate: (agent:string, model:string, mode:string, intent_lock?:unknown) => call<LiveSession>('/tester/sessions', {method:'POST',body:JSON.stringify({agent,model,mode,intent_lock})}),
  testerChat: (id:string,prompt:string) => call<LiveSession>(`/tester/sessions/${id}/chat`, {method:'POST',body:JSON.stringify({prompt})}),
  testerCompare: (agent:string,model:string,prompt:string,intent_lock?:unknown) => call<{before:LiveSession;after:LiveSession}>('/tester/compare', {method:'POST',body:JSON.stringify({agent,model,prompt,intent_lock})}),
  testerApproval: (id:string,approvalId:string,allow:boolean) => call<LiveSession>(`/tester/sessions/${id}/approvals/${approvalId}`, {method:'POST',headers:{Authorization:`Bearer ${ownerTokens.get(id) || ''}`},body:JSON.stringify({allow})}),
  scenarios: () => call<(Agent & { id: string })[]>('/scenarios'),
  analyze: (agent: Agent) => call<AnalysisResult>('/analyze', { method: 'POST', body: JSON.stringify(agent) }),
  simulate: (agent: Agent, remove_permission: string) => call<SimulationResult>('/simulate', { method: 'POST', body: JSON.stringify({ agent, remove_permission }) }),
  explain: (agent: Agent, analysis: AnalysisResult) => call<{ summary: string; why_it_matters: string; purpose_alignment: string; recommendation: string; source: string }>('/explain', { method: 'POST', body: JSON.stringify({ agent, analysis }) }),
  import: (agent: Agent) => call<{ agent: Agent; analysis: AnalysisResult }>('/import', { method: 'POST', body: JSON.stringify(agent) }),
  liveConfig: () => call<{ default_model: string; local_model_enabled: boolean; local_model_status: 'ready' | 'disabled' | 'unavailable' | 'not_installed' | 'load_failed' | 'load_timeout'; replay_available: boolean; sandbox_only: boolean }>('/live/config'),
  liveCreate: (options: { scenario: LiveScenario; mode: 'protected' | 'unprotected'; task?: string; model: 'replay' | 'local' }) => call<LiveSession>('/live/sessions', { method: 'POST', body: JSON.stringify(options) }),
  liveRun: (id: string) => call<LiveSession>(`/live/sessions/${id}/run`, { method: 'POST' }),
  liveGet: (id: string) => call<LiveSession>(`/live/sessions/${id}`),
  bankSignIn: (id: string, pin: string) => call<{ token: string }>(`/live/sessions/${id}/bank-sign-in`, { method: 'POST', body: JSON.stringify({ pin }) }),
  bankChat: (id: string, token: string, prompt: string, model = 'demo') => call<{ reply: string; session: LiveSession }>(`/live/sessions/${id}/bank-chat`, { method: 'POST', body: JSON.stringify({ token, prompt, model }) }),
  liveList: () => call<LiveSession[]>('/live/sessions'),
  liveAction: (id: string, tool: string, target: string, amount?: number) => call<{ session: LiveSession }>(`/live/sessions/${id}/actions`, { method: 'POST', body: JSON.stringify({ tool, target, amount }) }),
  liveApproval: (id: string, approvalId: string, allow: boolean) => call<{ session: LiveSession }>(`/live/sessions/${id}/approvals/${approvalId}`, { method: 'POST', headers: {Authorization: `Bearer ${ownerTokens.get(id) || ''}`}, body: JSON.stringify({ allow }) }),
  liveCompare: (scenario = 'coding', capturedId = '') => call<LiveComparison>(`/live/compare?scenario=${scenario}${capturedId ? '&captured_id='+encodeURIComponent(capturedId) : ''}`, { method: 'POST' }),
  practicalCreate: (mode: 'protected' | 'unprotected', model: 'qwen' | 'demo', injection: string, delegation_granted: boolean) => call<PracticalSession>('/live/practical/sessions', { method: 'POST', body: JSON.stringify({ mode, model, injection, delegation_granted }) }),
  practicalGet: (id: string) => call<PracticalSession>(`/live/practical/sessions/${id}`),
  practicalSignIn: (id: string, pin: string) => call<{ token: string; session: PracticalSession }>(`/live/practical/sessions/${id}/sign-in`, { method: 'POST', body: JSON.stringify({ pin }) }),
  practicalChat: (id: string, token: string, prompt: string) => call<PracticalSession>(`/live/practical/sessions/${id}/chat`, { method: 'POST', body: JSON.stringify({ token, prompt }) }),
}
export function liveSocketUrl(id: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/live/ws/${id}`
}
