from app.models import AgentInput
from app.engine.normalizer import normalize
from app.engine.risk_engine import detect
from app.engine.scoring import score
from app.engine.graph_engine import build_graph

PURPOSE_HINTS = {
    'support': {'DATA_READ_SENSITIVE', 'FILE_READ', 'DATA_WRITE', 'INTERNAL_SEND'},
    'ticket': {'DATA_READ_SENSITIVE', 'FILE_READ', 'DATA_WRITE', 'INTERNAL_SEND'},
    'deploy': {'CODE_READ', 'CODE_WRITE', 'CI_TRIGGER', 'DEPLOY'},
    'devops': {'CODE_READ', 'CODE_WRITE', 'CI_TRIGGER', 'DEPLOY'},
    'payment': {'DATA_READ_INTERNAL', 'PAYMENT_CREATE'},
    'invoice': {'DATA_READ_INTERNAL', 'PAYMENT_CREATE'},
}

def analyze(agent: AgentInput) -> dict:
    normalized = normalize(agent)
    capabilities = sorted({item['capability'] for item in normalized if item['capability']})
    risks = detect(normalized)
    value, severity = score(capabilities, risks)
    expected = set().union(*(v for k, v in PURPOSE_HINTS.items() if k in agent.purpose.lower()))
    alignment = []
    for item in normalized:
        capability = item['capability']
        status = 'Unknown / Review' if not capability else ('Necessary' if capability in expected else 'Unnecessary / Review' if expected else 'Possibly Necessary')
        alignment.append({'permission': item['permission'], 'status': status})
    recommendations = []
    for item in normalized:
        if item['capability'] == 'EXTERNAL_SEND' and any(r['id'] in ('DATA_EXFILTRATION', 'SECRET_EXFILTRATION') for r in risks):
            recommendations.append({'permission': item['permission'], 'reason': 'Breaks an external data path.'})
    return {'agent': agent.model_dump(), 'score': value, 'severity': severity,
            'capabilities': capabilities, 'normalized_permissions': normalized,
            'risks': risks, 'graph': build_graph(agent.name, normalized, risks),
            'alignment': alignment, 'recommendations': recommendations,
            'unknown_permissions': [i['permission'] for i in normalized if not i['capability']]}
