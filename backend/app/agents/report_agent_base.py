from abc import ABC, abstractmethod

from app.models.analysis_models import AnalysisLanguage, AgentStructuredOutput
from app.models.llm_models import ProviderName


class ReportExplanationAgent(ABC):
    @abstractmethod
    async def explain(
        self,
        confirmed_text: str,
        language: AnalysisLanguage,
        provider: ProviderName | None = None,
    ) -> tuple[AgentStructuredOutput, ProviderName, str, bool]:
        raise NotImplementedError
