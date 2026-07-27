from app.agents.common_report_agent import PromptDrivenReportAgent


class BloodReportAgent(PromptDrivenReportAgent):
    def __init__(self) -> None:
        super().__init__(
            "Explain a written blood/laboratory report. For each visible test, capture the test name, "
            "observed value, unit, reference range, report-marked status, and a plain-language description "
            "of what the test generally measures. Do not infer a status when the report does not provide "
            "enough information, and do not explain the cause of an abnormal value."
        )
