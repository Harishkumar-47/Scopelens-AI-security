import { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import type { Graph } from '../types'
export default function CapabilityGraph({ graph, compact = false }: { graph: Graph; compact?: boolean }) {
  const target = useRef<HTMLDivElement>(null)
  const [selected, setSelected] = useState('Select a node to inspect its role in the agent’s reach.')
  useEffect(() => {
    if (!target.current) return
    const cy = cytoscape({ container: target.current, elements: [
      ...graph.nodes.map(n => ({ data: n })), ...graph.edges.map(e => ({ data: e }))],
      style: [
        { selector: 'node', style: { 'background-color': '#253a56', 'label': 'data(label)', 'color': '#d9e7f5', 'font-size': compact ? '9px' : '11px', 'text-wrap': 'wrap', 'text-max-width': '100px', 'text-valign': 'bottom', 'text-margin-y': 8, 'width': 24, 'height': 24, 'border-width': 2, 'border-color': '#49607b' } },
        { selector: 'node[kind="agent"]', style: { 'background-color': '#50c8ed', 'border-color': '#b4f0ff', 'width': 44, 'height': 44, 'color': '#ffffff', 'font-weight': 700 } },
        { selector: 'node[kind="resource"]', style: { 'background-color': '#135b72', 'border-color': '#36b7d9', 'shape': 'round-rectangle', 'width': 36, 'height': 28 } },
        { selector: 'node[kind="permission"]', style: { 'background-color': '#32465e', 'border-color': '#8097b2', 'shape': 'round-rectangle', 'width': 30, 'height': 22 } },
        { selector: 'node[kind="risk"]', style: { 'background-color': '#e55767', 'border-color': '#ff9b9b', 'width': 35, 'height': 35, 'font-weight': 700 } },
        { selector: 'edge', style: { 'width': 1.8, 'line-color': '#4a6784', 'target-arrow-color': '#4a6784', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'opacity': .7 } },
        { selector: 'edge[dangerous]', style: { 'width': 3, 'line-color': '#f36b75', 'target-arrow-color': '#f36b75', 'opacity': 1 } },
        { selector: '.highlighted', style: { 'overlay-color': '#52d6f7', 'overlay-opacity': .18, 'overlay-padding': 6 } }
      ], layout: { name: 'breadthfirst', directed: true, padding: 42, spacingFactor: 1.25, animate: false }, minZoom: .3, maxZoom: 2.3, wheelSensitivity: .16 })
    cy.on('tap', 'node', event => { const node = event.target; cy.elements().removeClass('highlighted'); node.addClass('highlighted'); node.neighborhood().addClass('highlighted'); setSelected(`${node.data('label')} · ${node.data('kind')}`) })
    return () => cy.destroy()
  }, [graph, compact])
  return <div className="graph-wrap"><div ref={target} className={compact ? 'graph compact' : 'graph'} role="img" aria-label="Interactive agent capability graph"/><div className="graph-hint">{selected} <span>Scroll to zoom · drag to explore</span></div></div>
}
