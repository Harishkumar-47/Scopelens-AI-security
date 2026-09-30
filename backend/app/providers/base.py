from abc import ABC, abstractmethod
from app.models import AgentInput

class ProviderAdapter(ABC):
    @abstractmethod
    def permissions(self, agent: AgentInput) -> list[str]:
        raise NotImplementedError
