import type { Agent, AnalysisResult, SimulationResult } from '../types'
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
}
