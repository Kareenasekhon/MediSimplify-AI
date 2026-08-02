from threading import RLock

from app.core.config import settings
from app.models.chat_models import ChatMessage


class ChatMemoryService:
    """Bounded short-lived conversation history isolated by report ID."""

    def __init__(self, max_messages: int | None = None) -> None:
        self.max_messages = max_messages or settings.chat_history_max_messages
        self._history: dict[str, list[ChatMessage]] = {}
        self._lock = RLock()

    def get(self, report_id: str) -> list[ChatMessage]:
        with self._lock:
            return list(self._history.get(report_id, []))

    def add_turn(self, report_id: str, question: str, answer: str) -> None:
        with self._lock:
            history = self._history.setdefault(report_id, [])
            history.extend([
                ChatMessage(role="user", content=question),
                ChatMessage(role="assistant", content=answer),
            ])
            self._history[report_id] = history[-self.max_messages :]

    def clear(self, report_id: str) -> bool:
        with self._lock:
            return self._history.pop(report_id, None) is not None


chat_memory_service = ChatMemoryService()
