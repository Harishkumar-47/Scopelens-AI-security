import { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import type { Graph } from '../types'
import { useTheme } from '../theme'
const accessLabels: Record<string, string> = {
  DATA_READ_SENSITIVE: 'Read private data', EXTERNAL_SEND: 'Send outside', SECRET_READ: 'Read passwords',
  FILE_READ: 'Read files', DATA_WRITE: 'Change data', DATA_DELETE: 'Delete data', CODE_READ: 'Read code',
  CODE_WRITE: 'Change code', CI_TRIGGER: 'Run build', DEPLOY: 'Deploy', PAYMENT_CREATE: 'Prepare payment',
  PAYMENT_APPROVE: 'Approve payment', CLOUD_ADMIN: 'Manage cloud', EXECUTE_COMMAND: 'Run commands',
}
export default function CapabilityGraph({ graph, compact = false }: { graph: Graph; compact?: boolean }) {
  const target = useRef<HTMLDivElement>(null)
  const [selected, setSelected] = useState('Select a picture to see what it means.')
  const { theme } = useTheme()
  useEffect(() => {
    if (!target.current) return
    const variables = getComputedStyle(document.documentElement)
    const color = (key: string) => variables.getPropertyValue(key).trim()
    const cy = cytoscape({ container: target.current, elements: [
      ...graph.nodes.map(n => ({ data: { ...n, label: n.kind === 'capability' ? accessLabels[n.id.replace('capability:', '')] || n.label : n.label } })), ...graph.edges.map(e => ({ data: e }))],
      style: [
        { selector: 'node', style: { 'background-color': color('--graph-node'), 'label': 'data(label)', 'color': color('--graph-text'), 'font-size': compact ? '9px' : '11px', 'text-wrap': 'wrap', 'text-max-width': '100px', 'text-valign': 'bottom', 'text-margin-y': 8, 'width': 24, 'height': 24, 'border-width': 2, 'border-color': color('--graph-border') } },
        { selector: 'node[kind="agent"]', style: { 'background-color': color('--graph-agent'), 'border-color': color('--graph-agent'), 'width': 44, 'height': 44, 'font-weight': 700 } },
        { selector: 'node[kind="resource"]', style: { 'background-color': color('--graph-resource'), 'border-color': color('--graph-border'), 'shape': 'round-rectangle', 'width': 36, 'height': 28 } },
        { selector: 'node[kind="permission"]', style: { 'background-color': color('--graph-node'), 'border-color': color('--graph-border'), 'shape': 'round-rectangle', 'width': 30, 'height': 22 } },
        { selector: 'node[kind="risk"]', style: { 'background-color': color('--danger'), 'border-color': color('--danger'), 'width': 35, 'height': 35, 'font-weight': 700 } },
        { selector: 'edge', style: { 'width': 1.8, 'line-color': color('--graph-edge'), 'target-arrow-color': color('--graph-edge'), 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'opacity': .75 } },
        { selector: 'edge[dangerous]', style: { 'width': 3, 'line-color': color('--danger'), 'target-arrow-color': color('--danger'), 'opacity': 1 } },
        { selector: '.highlighted', style: { 'overlay-color': color('--danger'), 'overlay-opacity': .12, 'overlay-padding': 6 } }
      ], layout: { name: 'breadthfirst', directed: true, padding: 42, spacingFactor: 1.25, animate: false }, minZoom: .3, maxZoom: 2.3, wheelSensitivity: .16 })
    cy.on('tap', 'node', event => { const node = event.target; cy.elements().removeClass('highlighted'); node.addClass('highlighted'); node.neighborhood().addClass('highlighted'); setSelected(`${node.data('label')} · ${node.data('kind')}`) })
    return () => cy.destroy()
  }, [graph, compact, theme])
  return <div className="graph-wrap"><div ref={target} className={compact ? 'graph compact' : 'graph'} role="img" aria-label="Interactive AI access map"/><div className="graph-hint">{selected} <span>Scroll to zoom · drag to explore</span></div></div>
}
