from app.models import AgentInput
from app.providers.base import ProviderAdapter

class MCPAdapter(ProviderAdapter):
    def permissions(self, agent: AgentInput) -> list[str]:
        result = list(agent.permissions)
        for tool in (agent.manifest or {}).get('tools', []):
            if isinstance(tool, dict):
                for capability in tool.get('capabilities', []):
                    result.append(f"mcp.{tool.get('name', 'tool')}.{capability}")
        return list(dict.fromkeys(result))
