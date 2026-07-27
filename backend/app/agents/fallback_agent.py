from app.agents.common_report_agent import PromptDrivenReportAgent


class FallbackAgent(PromptDrivenReportAgent):
    def __init__(self) -> None:
        super().__init__(
            "Handle an unsupported, mixed, incomplete, or unclear written medical document. Summarize only "
            "what is clearly present, separate unclear information, and explain that specialized interpretation "
            "was not possible where appropriate."
        )
