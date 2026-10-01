import { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import type { LiveGraph as LiveGraphType } from '../types'
import { useTheme } from '../theme'

export default function LiveGraph({ graph, showAuthority = false, compact = false }: {
  graph: LiveGraphType; showAuthority?: boolean; compact?: boolean
}) {
  const container = useRef<HTMLDivElement>(null)
  const [selected, setSelected] = useState('Select a picture to learn more')
  const { theme } = useTheme()

  useEffect(() => {
    if (!container.current) return
    const variables = getComputedStyle(document.documentElement)
    const color = (key: string) => variables.getPropertyValue(key).trim()
    const nodes = graph.nodes.filter(node => showAuthority || !node.latent)
    const ids = new Set(nodes.map(node => node.id))
    const edges = graph.edges.filter(edge => (showAuthority || !edge.latent) && ids.has(edge.source) && ids.has(edge.target))
    const cy = cytoscape({
      container: container.current,
      elements: [...nodes.map(node => ({ data: node })), ...edges.map(edge => ({ data: edge }))],
      style: [
        { selector: 'node', style: { label: 'data(label)', 'text-wrap': 'wrap', 'text-max-width': '110px', 'font-size': compact ? '9px' : '11px', 'text-valign': 'bottom', 'text-margin-y': 8, color: color('--graph-text'), 'background-color': color('--graph-node'), 'border-width': 2, 'border-color': color('--graph-border'), width: 31, height: 31 } },
        { selector: 'node[kind="agent"]', style: { 'background-color': color('--graph-agent'), 'border-color': color('--graph-agent'), width: 48, height: 48, 'font-weight': 700 } },
        { selector: 'node[kind="tool"]', style: { shape: 'round-rectangle', width: 36, height: 28 } },
        { selector: 'node[kind="resource"]', style: { shape: 'round-rectangle', width: 38, height: 30 } },
        { selector: 'node[state="allowed"]', style: { 'background-color': color('--safe'), 'border-color': color('--safe') } },
        { selector: 'node[state="warning"]', style: { 'background-color': color('--warning'), 'border-color': color('--warning') } },
        { selector: 'node[state="approval"]', style: { 'background-color': color('--warning'), 'border-color': color('--warning') } },
        { selector: 'node[state="critical"], node[state="blocked"]', style: { 'background-color': color('--danger'), 'border-color': color('--danger') } },
        { selector: 'node[kind="outcome"]', style: { width: 43, height: 43, 'font-weight': 700 } },
        { selector: 'edge', style: { width: 2, 'line-color': color('--graph-edge'), 'target-arrow-color': color('--graph-edge'), 'target-arrow-shape': 'triangle', 'curve-style': 'bezier' } },
        { selector: 'edge[state="allowed"]', style: { 'line-color': color('--safe'), 'target-arrow-color': color('--safe') } },
        { selector: 'edge[state="warning"], edge[state="approval"]', style: { 'line-color': color('--warning'), 'target-arrow-color': color('--warning') } },
        { selector: 'edge[state="critical"], edge[state="blocked"]', style: { width: 3, 'line-color': color('--danger'), 'target-arrow-color': color('--danger') } },
      ],
      layout: { name: 'breadthfirst', directed: true, padding: 28, spacingFactor: 1.35, animate: false },
      minZoom: .28, maxZoom: 2.3, wheelSensitivity: .15,
    })
    cy.on('tap', 'node', event => setSelected(`${event.target.data('label')} · ${event.target.data('state')}`))
    return () => cy.destroy()
  }, [graph, showAuthority, compact, theme])

  return <div className="live-graph-wrap"><div ref={container} className={compact ? 'live-graph compact' : 'live-graph'} role="img" aria-label="AI access and action map"/><div className="graph-caption">{selected}<span>Drag to explore · scroll to zoom</span></div></div>
}
