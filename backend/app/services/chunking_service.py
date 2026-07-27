import re

from app.models.rag_models import ReportChunk


def chunk_report_text(
    report_id: str,
    text: str,
    chunk_size: int = 900,
    overlap: int = 140,
) -> list[ReportChunk]:
    """Split confirmed report text into stable, overlapping chunks."""
    normalized = re.sub(r"[ \t]+", " ", text).strip()
    if not normalized:
        return []
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    paragraphs = [part.strip() for part in re.split(r"\n{2,}|(?<=\.)\s+", normalized) if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current} {paragraph}".strip()
        if current and len(candidate) > chunk_size:
            chunks.append(current)
            prefix = current[-overlap:].strip()
            current = f"{prefix} {paragraph}".strip()
            while len(current) > chunk_size:
                chunks.append(current[:chunk_size].strip())
                current = current[chunk_size - overlap :].strip()
        else:
            current = candidate

    if current:
        chunks.append(current)

    deduplicated: list[str] = []
    for value in chunks:
        if value and (not deduplicated or value != deduplicated[-1]):
            deduplicated.append(value)

    return [
        ReportChunk(
            chunk_id=f"{report_id}_chunk_{index + 1}",
            report_id=report_id,
            text=value,
            order=index,
            metadata={"character_count": len(value)},
        )
        for index, value in enumerate(deduplicated)
    ]
