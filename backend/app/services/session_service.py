from typing import Dict, Any

# In-memory active session store
_SESSIONS: Dict[str, Dict[str, Any]] = {}

def get_session(report_id: str) -> Dict[str, Any]:
    """
    Retrieves the session data for a given report_id.
    """
    return _SESSIONS.get(report_id, {})

def create_session(report_id: str, data: Dict[str, Any]) -> None:
    """
    Registers a new session with report details.
    """
    _SESSIONS[report_id] = data

def update_session(report_id: str, updates: Dict[str, Any]) -> None:
    """
    Updates an existing report session.
    """
    if report_id in _SESSIONS:
        _SESSIONS[report_id].update(updates)

def delete_session(report_id: str) -> None:
    """
    Deletes the active session from memory.
    """
    if report_id in _SESSIONS:
        del _SESSIONS[report_id]
