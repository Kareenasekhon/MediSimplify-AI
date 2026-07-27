from app.agents.common_report_agent import PromptDrivenReportAgent


class RadiologyAgent(PromptDrivenReportAgent):
    def __init__(self) -> None:
        super().__init__(
            "Explain only a written radiology report, including modality/body part, findings, impression, and "
            "follow-up wording already present. Simplify medical terms without interpreting raw X-ray, MRI, "
            "CT, or ultrasound images and without adding conclusions not written by the radiologist."
        )
