from abc import ABC, abstractmethod

from app.models.routing_models import RoutingResult


class BaseAgent(ABC):
    """Minimal agent contract used by the supervisor phase."""

    @abstractmethod
    async def run(self, report_id: str, confirmed_text: str) -> RoutingResult:
        raise NotImplementedError
