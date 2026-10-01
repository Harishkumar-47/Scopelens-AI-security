import type { Agent, AnalysisResult, SimulationResult, LiveSession, LiveComparison, LiveScenario } from '../types'
async function call<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...options?.headers } })
  if (!response.ok) throw new Error((await response.text()).slice(0, 300))
  return response.json() as Promise<T>
}
export const api = {
  scenarios: () => call<(Agent & { id: string })[]>('/scenarios'),
  analyze: (agent: Agent) => call<AnalysisResult>('/analyze', { method: 'POST', body: JSON.stringify(agent) }),
  simulate: (agent: Agent, remove_permission: string) => call<SimulationResult>('/simulate', { method: 'POST', body: JSON.stringify({ agent, remove_permission }) }),
  explain: (agent: Agent, analysis: AnalysisResult) => call<{ summary: string; why_it_matters: string; purpose_alignment: string; recommendation: string; source: string }>('/explain', { method: 'POST', body: JSON.stringify({ agent, analysis }) }),
  import: (agent: Agent) => call<{ agent: Agent; analysis: AnalysisResult }>('/import', { method: 'POST', body: JSON.stringify(agent) }),
  liveConfig: () => call<{ default_model: string; local_model_enabled: boolean; replay_available: boolean; sandbox_only: boolean }>('/live/config'),
  liveCreate: (options: { scenario: LiveScenario; mode: 'protected' | 'unprotected'; task?: string; model: 'replay' | 'local' }) => call<LiveSession>('/live/sessions', { method: 'POST', body: JSON.stringify(options) }),
  liveRun: (id: string) => call<LiveSession>(`/live/sessions/${id}/run`, { method: 'POST' }),
  liveGet: (id: string) => call<LiveSession>(`/live/sessions/${id}`),
  liveList: () => call<LiveSession[]>('/live/sessions'),
  liveAction: (id: string, tool: string, target: string, amount?: number) => call<{ session: LiveSession }>(`/live/sessions/${id}/actions`, { method: 'POST', body: JSON.stringify({ tool, target, amount }) }),
  liveApproval: (id: string, approvalId: string, allow: boolean) => call<{ session: LiveSession }>(`/live/sessions/${id}/approvals/${approvalId}`, { method: 'POST', body: JSON.stringify({ allow }) }),
  liveCompare: () => call<LiveComparison>('/live/compare', { method: 'POST' }),
}
export function liveSocketUrl(id: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/live/ws/${id}`
}
