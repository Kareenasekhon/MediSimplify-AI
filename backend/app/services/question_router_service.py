import re
from dataclasses import dataclass

from app.models.chat_models import ChatMode


_REPORT_PATTERNS = (
    r"\bmy\b",
    r"\bmine\b",
    r"\bthis report\b",
    r"\buploaded report\b",
    r"\bresult(?:s)?\b",
    r"\bvalue(?:s)?\b",
    r"\blevel(?:s)?\b",
    r"\breading(?:s)?\b",
    r"\bprescribed\b",
    r"\bdos(?:e|age)\b",
    r"\bfindings?\b",
    r"\bimpression\b",
    r"\breference range\b",
    r"\bhigh\b",
    r"\blow\b",
    r"\bnormal\b",
)

_GENERAL_PATTERNS = (
    r"^\s*what (?:is|are|does)\b",
    r"^\s*define\b",
    r"^\s*explain\b",
    r"\bmeaning of\b",
    r"\bwhat does .* mean\b",
    r"\bhow does .* work\b",
    r"\bwhy (?:is|are|does)\b",
)


@dataclass(frozen=True)
class QuestionRoute:
    mode: ChatMode
    reason: str


def classify_question(question: str, has_history: bool = False) -> QuestionRoute:
    """Classify a chat question without making an extra billable LLM request."""
    text = re.sub(r"\s+", " ", question.strip().lower())
    report_score = sum(bool(re.search(pattern, text)) for pattern in _REPORT_PATTERNS)
    general_score = sum(bool(re.search(pattern, text)) for pattern in _GENERAL_PATTERNS)

    # Short follow-ups commonly depend on the immediately preceding answer.
    if has_history and len(text.split()) <= 8 and not general_score:
        report_score += 1

    if report_score and general_score:
        return QuestionRoute(
            mode=ChatMode.HYBRID,
            reason="The question asks about the report and also requests a medical explanation.",
        )
    if report_score:
        return QuestionRoute(
            mode=ChatMode.REPORT,
            reason="The question refers to patient-specific report information.",
        )
    if general_score:
        return QuestionRoute(
            mode=ChatMode.EDUCATIONAL,
            reason="The question asks for a general medical concept or definition.",
        )
    return QuestionRoute(
        mode=ChatMode.REPORT,
        reason="The question was conservatively routed to report-grounded mode.",
    )
