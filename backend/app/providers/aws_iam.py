from app.models import AgentInput
from app.providers.base import ProviderAdapter

class AWSIAMAdapter(ProviderAdapter):
    def permissions(self, agent: AgentInput) -> list[str]:
        result = list(agent.permissions)
        statements = (agent.manifest or {}).get('Statement', [])
        if isinstance(statements, dict):
            statements = [statements]
        for statement in statements:
            if statement.get('Effect') != 'Allow':
                continue
            actions = statement.get('Action', [])
            result.extend([actions] if isinstance(actions, str) else actions)
        return list(dict.fromkeys(result))
