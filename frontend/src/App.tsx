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
        <NavLink to="/new">Agent Analyzer</NavLink>
        <NavLink to="/live">Live Agent Lab</NavLink>
        <NavLink to="/activity">Activity</NavLink>
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
      <Route path="/about" element={<section className="page narrow about-page"><div className="eyebrow"><ShieldCheck size={16}/> THE SCOPELENS MISSION</div><h1>See authority. Guard action.</h1><p className="lead">Before deployment, ScopeLens shows what an AI agent could do with combined permissions. During execution, it shows what the agent is actually trying to access and blocks scope deviations through code outside the model.</p><div className="panel"><h2>Two layers of clarity</h2><p><strong>Analyze</strong> normalizes permissions, builds a capability graph and simulates least-privilege changes. <strong>Live</strong> routes every sandbox tool request through an ALLOW / ASK / BLOCK policy and streams activity to the graph.</p><p className="muted">This is a local hackathon prototype. The Live Lab contains only synthetic data and a local fake send sink. Provider imports model a supported subset and do not replace provider-native controls.</p></div></section>}/>
    </Routes></main>
    <footer><span>© ScopeLens · Sandbox prototype</span><span>See the blast radius. Watch the movement. Guard the action.</span></footer>
  </div>
}
