import re
from collections import Counter

from app.agents.supervisor_agent import REPORT_TYPE_TO_AGENT, SupervisorAgent
from app.core.exceptions import ProviderError, ValidationError
from app.models.llm_models import ProviderName
from app.models.routing_models import ReportType, RoutingResult


KEYWORDS = {
    ReportType.BLOOD_REPORT: {
        "cbc", "hemoglobin", "haemoglobin", "wbc", "rbc", "platelet",
        "platelets", "glucose", "creatinine", "bilirubin", "cholesterol",
        "reference range", "mg/dl", "g/dl", "cells/cumm", "test result",
    },
    ReportType.PRESCRIPTION: {
        "rx", "tablet", "tab", "capsule", "cap", "syrup", "injection",
        "dose", "dosage", "once daily", "twice daily", "thrice daily",
        "od", "bd", "tds", "before food", "after food", "for days",
    },
    ReportType.RADIOLOGY_REPORT: {
        "x-ray", "xray", "mri", "ct scan", "ultrasound", "sonography",
        "radiologist", "findings", "impression", "clinical correlation",
        "contrast", "scan", "radiology",
    },
}

MIN_RULE_SCORE = 3
MIN_SCORE_MARGIN = 2


def _keyword_scores(text: str) -> Counter[ReportType]:
    lowered = re.sub(r"\s+", " ", text.lower())
    scores: Counter[ReportType] = Counter()
    for report_type, keywords in KEYWORDS.items():
        for keyword in keywords:
            if re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", lowered):
                scores[report_type] += 1
    return scores


def _rule_result(report_id: str, text: str) -> RoutingResult | None:
    scores = _keyword_scores(text)
    ranked = scores.most_common()
    if not ranked:
        return None

    top_type, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0
    multiple_strong = len([score for _, score in ranked if score >= MIN_RULE_SCORE]) > 1

    if multiple_strong and top_score - second_score < MIN_SCORE_MARGIN:
        return RoutingResult(
            report_id=report_id,
            report_type=ReportType.MIXED_REPORT,
            confidence=0.55,
            selected_agent=REPORT_TYPE_TO_AGENT[ReportType.MIXED_REPORT],
            reason="Strong indicators for more than one report category were detected.",
            warnings=["This may be a mixed report. Please confirm the route manually."],
            requires_manual_selection=True,
            method="rules",
        )

    if top_score >= MIN_RULE_SCORE and top_score - second_score >= MIN_SCORE_MARGIN:
        confidence = min(0.98, 0.72 + top_score * 0.04)
        return RoutingResult(
            report_id=report_id,
            report_type=top_type,
            confidence=confidence,
            selected_agent=REPORT_TYPE_TO_AGENT[top_type],
            reason=(
                f"Deterministic routing detected {top_score} indicators for "
                f"{top_type.value.replace('_', ' ')}."
            ),
            method="rules",
        )
    return None


async def route_report(
    report_id: str,
    confirmed_text: str,
    preferred_provider: ProviderName | None = None,
) -> RoutingResult:
    text = confirmed_text.strip()
    if len(text) < 10:
        raise ValidationError("Confirmed report text is too short to classify safely.")

    deterministic = _rule_result(report_id, text)
    if deterministic is not None:
        return deterministic

    try:
        return await SupervisorAgent().classify(report_id, text, preferred_provider)
    except (ProviderError, ValueError) as exc:
        return RoutingResult(
            report_id=report_id,
            report_type=ReportType.UNKNOWN,
            confidence=0.0,
            selected_agent=REPORT_TYPE_TO_AGENT[ReportType.UNKNOWN],
            reason="Automatic report classification was unavailable.",
            warnings=[
                "Select the report type manually before continuing.",
                str(exc),
            ],
            requires_manual_selection=True,
            method="fallback",
        )


def apply_manual_route(report_id: str, report_type: ReportType) -> RoutingResult:
    return RoutingResult(
        report_id=report_id,
        report_type=report_type,
        confidence=1.0,
        selected_agent=REPORT_TYPE_TO_AGENT[report_type],
        reason="The report type was selected manually by the user.",
        requires_manual_selection=False,
        method="manual",
    )
