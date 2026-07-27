from app.agents.common_report_agent import PromptDrivenReportAgent


class PrescriptionAgent(PromptDrivenReportAgent):
    def __init__(self) -> None:
        super().__init__(
            "Explain a written prescription. Capture each medicine name, strength/value, dosage, frequency, "
            "duration, and written instructions exactly as shown. Explain only what the written instruction "
            "means in plain language. Never add a dose, infer an unreadable medicine, or alter instructions."
        )
