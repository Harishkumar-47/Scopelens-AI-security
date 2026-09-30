import networkx as nx

RESOURCE_NAMES = {'DATA_READ_SENSITIVE': 'Customer Database', 'FILE_READ': 'Drive Files',
                  'EXTERNAL_SEND': 'External Email', 'SECRET_READ': 'Secrets Vault',
                  'CODE_WRITE': 'Source Repository', 'DEPLOY': 'Production',
                  'PAYMENT_CREATE': 'Payment Platform', 'PAYMENT_APPROVE': 'Payment Platform'}

def build_graph(agent_name: str, normalized: list[dict], risks: list[dict]) -> dict:
    graph = nx.DiGraph()
    dangerous_capabilities = {capability for risk in risks for capability in risk['required_capabilities']}
    graph.add_node('agent', label=agent_name, kind='agent')
    for item in normalized:
        permission = item['permission']
        capability = item['capability']
        pid = f'permission:{permission}'
        graph.add_node(pid, label=permission, kind='permission')
        graph.add_edge('agent', pid, kind='grants', dangerous=capability in dangerous_capabilities)
        if capability:
            cid = f'capability:{capability}'
            graph.add_node(cid, label=capability.replace('_', ' ').title(), kind='capability')
            graph.add_edge(pid, cid, kind='enables', dangerous=capability in dangerous_capabilities)
            if capability in RESOURCE_NAMES:
                rid = f'resource:{RESOURCE_NAMES[capability]}'
                graph.add_node(rid, label=RESOURCE_NAMES[capability], kind='resource')
                graph.add_edge(cid, rid, kind='reaches', dangerous=capability in dangerous_capabilities)
    for risk in risks:
        rid = f'risk:{risk["id"]}'
        graph.add_node(rid, label=risk['name'], kind='risk', severity=risk['severity'])
        for capability in risk['required_capabilities']:
            graph.add_edge(f'capability:{capability}', rid, kind='chain', dangerous=True)
    shortest_paths = {risk['id']: [nx.shortest_path(graph, 'agent', f'capability:{capability}')
                                   for capability in risk['required_capabilities']] for risk in risks}
    nodes = [{'id': node, **data} for node, data in graph.nodes(data=True)]
    edges = [{'id': f'{source}->{target}', 'source': source, 'target': target,
              **{key: value for key, value in data.items() if key != 'dangerous' or value}}
             for source, target, data in graph.edges(data=True)]
    sensitive = ['resource:Customer Database', 'resource:Secrets Vault']
    return {'nodes': nodes, 'edges': edges,
            'metadata': {'reachable_sensitive_resources': [s for s in sensitive if s in graph and nx.has_path(graph, 'agent', s)],
                         'reachable_outcomes': [n for n in graph if n.startswith('risk:') and nx.has_path(graph, 'agent', n)],
                         'shortest_paths': shortest_paths}}
