import type { AnalysisResult } from '../types'
export default function RiskScore({ result }: { result: AnalysisResult }) {
  return <div className={`score-card severity-${result.severity.toLowerCase()}`}><div className="overline">SCOPELENS EXPOSURE SCORE</div><div className="score-line"><strong>{result.score}</strong><span>/ 100</span></div><div className="severity-row"><span className="severity-pill">{result.severity}</span><span>Deterministic assessment</span></div><div className="score-track"><span style={{ width: `${result.score}%` }}/></div><p>Based on capabilities and detected combinations. This is a ScopeLens model, not an industry standard.</p></div>
}
