from app.models import AgentInput
from app.providers.base import ProviderAdapter

class AzureRBACAdapter(ProviderAdapter):
    def permissions(self, agent: AgentInput) -> list[str]:
        return list(dict.fromkeys(agent.permissions + (agent.manifest or {}).get('actions', [])))
