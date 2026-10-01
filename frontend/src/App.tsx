import { NavLink, Route, Routes } from 'react-router-dom'
import { Crosshair, Github, Moon, ShieldCheck, Sun } from 'lucide-react'
import { useTheme } from './theme'
import Landing from './pages/Landing'
import NewAnalysis from './pages/NewAnalysis'
import Analysis from './pages/Analysis'
import Compare from './pages/Compare'
import Scenarios from './pages/Scenarios'
import LiveLab from './pages/LiveLab'
import LiveCompare from './pages/LiveCompare'
import Activity from './pages/Activity'

export default function App() {
  const { theme, toggle } = useTheme()
  return <div className="app-shell">
    <header className="site-header">
      <NavLink to="/" className="brand"><span className="brand-icon"><Crosshair size={21}/></span><span>Scope<span className="accent">Lens</span></span></NavLink>
      <nav aria-label="Main navigation">
        <NavLink to="/" end>Dashboard</NavLink>
        <NavLink to="/new">Analyze</NavLink>
        <NavLink to="/live">Live</NavLink>
        <NavLink to="/activity">Alerts</NavLink>
        <NavLink to="/scenarios">Scenarios</NavLink>
        <NavLink to="/about">About</NavLink>
      </nav>
      <div className="header-actions"><button className="theme-toggle" onClick={toggle} aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`} title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}>{theme === 'light' ? <Moon size={18}/> : <Sun size={18}/>}</button><a className="header-link" href="https://github.com/Harishkumar-47/Scopelens-AI-security" target="_blank" rel="noreferrer" aria-label="ScopeLens on GitHub"><Github size={18}/></a></div>
    </header>
    <main><Routes>
      <Route path="/" element={<Landing/>}/>
      <Route path="/new" element={<NewAnalysis/>}/>
      <Route path="/analysis" element={<Analysis/>}/>
      <Route path="/compare" element={<Compare/>}/>
      <Route path="/live" element={<LiveLab/>}/>
      <Route path="/live/compare" element={<LiveCompare/>}/>
      <Route path="/activity" element={<Activity/>}/>
      <Route path="/scenarios" element={<Scenarios/>}/>
      <Route path="/about" element={<section className="page narrow about-page"><div className="eyebrow"><ShieldCheck size={16}/> ABOUT SCOPELENS</div><h1>AI has a job. Keep it there.</h1><p className="lead">ScopeLens shows what AI can access before you use it, then watches what it actually tries to do.</p><div className="panel"><h2>How it works</h2><p><strong>Analyze</strong> checks access across connected tools. <strong>Live</strong> checks every demo action in code and can allow, ask you, or block it.</p><details><summary>Technical details</summary><p>Permission mapping, graph analysis, and sandbox tool decisions are deterministic. The optional local model proposes actions but cannot enforce policy or call tools directly.</p></details><p className="muted">This prototype uses only synthetic files, fake money, and a local demo receiver. Provider imports cover a documented subset.</p></div></section>}/>
    </Routes></main>
    <footer><span>© ScopeLens · Safe sandbox demo</span><span>Your AI has a job. ScopeLens makes sure it stays within that job.</span></footer>
  </div>
}
