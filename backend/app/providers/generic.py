from app.models import AgentInput
from app.providers.base import ProviderAdapter

class GenericAdapter(ProviderAdapter):
    def permissions(self, agent: AgentInput) -> list[str]:
        return list(dict.fromkeys(p.strip() for p in agent.permissions if p.strip()))
