"""Local, privacy-aware report history storage for MediSimplify AI."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import os
from threading import RLock
from typing import Any, Mapping

FRONTEND_DIR = Path(__file__).resolve().parents[1]
HISTORY_PATH = Path(
    os.environ.get(
        "REPORT_HISTORY_PATH",
        str(FRONTEND_DIR / "data" / "report_history.json"),
    )
)
_LOCK = RLock()
_MAX_ENTRIES = 100


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _empty_store() -> dict[str, Any]:
    return {"version": 1, "reports": []}


def _ensure_store() -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not HISTORY_PATH.exists():
        HISTORY_PATH.write_text(json.dumps(_empty_store(), indent=2), encoding="utf-8")


def _read_store() -> dict[str, Any]:
    _ensure_store()
    try:
        payload = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = _empty_store()
    if not isinstance(payload, dict) or not isinstance(payload.get("reports"), list):
        payload = _empty_store()
    return payload


def _write_store(payload: Mapping[str, Any]) -> None:
    _ensure_store()
    temp_path = HISTORY_PATH.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(HISTORY_PATH)


def _entry_digest(entry: Mapping[str, Any]) -> str:
    stable = {
        "report_id": entry.get("report_id"),
        "filename": entry.get("filename"),
        "report_type": entry.get("report_type"),
        "language": entry.get("language"),
        "analysis": entry.get("analysis"),
    }
    encoded = json.dumps(_json_safe(stable), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def save_report(
    *,
    report_id: str,
    filename: str,
    report_type: str,
    language: str,
    provider: str,
    analysis: Mapping[str, Any],
    routing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Insert or update one structured report-history entry."""
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "report_id": str(report_id),
        "filename": filename or "medical_report",
        "report_type": report_type or "medical_report",
        "language": language or "English",
        "provider": provider or str(analysis.get("provider_used") or "unknown"),
        "created_at": now,
        "updated_at": now,
        "summary": str(analysis.get("summary") or ""),
        "analysis": _json_safe(dict(analysis)),
        "routing": _json_safe(dict(routing or {})),
    }
    entry["digest"] = _entry_digest(entry)

    with _LOCK:
        store = _read_store()
        reports = store["reports"]
        existing_index = next(
            (index for index, item in enumerate(reports) if str(item.get("report_id")) == str(report_id)),
            None,
        )
        if existing_index is not None:
            previous = reports[existing_index]
            entry["created_at"] = previous.get("created_at", now)
            if previous.get("digest") == entry["digest"]:
                return deepcopy(previous)
            reports[existing_index] = entry
        else:
            reports.append(entry)

        reports.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        store["reports"] = reports[:_MAX_ENTRIES]
        _write_store(store)
    return deepcopy(entry)


def list_reports() -> list[dict[str, Any]]:
    with _LOCK:
        reports = _read_store().get("reports", [])
    return deepcopy(reports)


def get_report(report_id: str) -> dict[str, Any] | None:
    for item in list_reports():
        if str(item.get("report_id")) == str(report_id):
            return item
    return None


def delete_report(report_id: str) -> bool:
    with _LOCK:
        store = _read_store()
        before = len(store["reports"])
        store["reports"] = [
            item for item in store["reports"]
            if str(item.get("report_id")) != str(report_id)
        ]
        changed = len(store["reports"]) != before
        if changed:
            _write_store(store)
    return changed


def clear_history() -> int:
    with _LOCK:
        store = _read_store()
        count = len(store.get("reports", []))
        _write_store(_empty_store())
    return count
