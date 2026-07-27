import os
from typing import Any, Dict, Optional

import httpx


class APIClient:
    """HTTP client for the MediSimplify FastAPI backend."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (
            base_url
            or os.environ.get("BACKEND_API_URL", "http://localhost:8000")
        ).rstrip("/")
        self.timeout = httpx.Timeout(120.0, connect=10.0)

    def check_health(self) -> Dict[str, Any]:
        """Query the backend health endpoint."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/api/v1/health")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            return {
                "status": "unhealthy",
                "error": self._extract_error(exc.response),
            }
        except httpx.RequestError as exc:
            return {
                "status": "unhealthy",
                "error": f"Failed to connect to backend: {exc}",
            }

    def extract_report(
        self,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> Dict[str, Any]:
        """Upload one report and return its extraction response."""
        files = {"file": (filename, content, content_type)}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/v1/reports/extract",
                    files=files,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(self._extract_error(exc.response)) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Could not reach the extraction API: {exc}") from exc

    def confirm_extraction(
        self,
        report_id: str,
        confirmed_text: str,
        corrected_structured_data: Dict[str, Any],
        language: str,
        provider: str,
    ) -> Dict[str, Any]:
        """Confirm user-reviewed extraction data."""
        payload = {
            "confirmed_text": confirmed_text,
            "corrected_structured_data": corrected_structured_data,
            "language": language,
            "provider": provider,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/v1/reports/{report_id}/confirm-analysis",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(self._extract_error(exc.response)) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Could not reach the confirmation API: {exc}") from exc

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        try:
            payload = response.json()
            return str(payload.get("message") or payload.get("detail") or payload)
        except ValueError:
            return f"Backend returned HTTP {response.status_code}."
