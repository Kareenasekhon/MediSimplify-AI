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

    def get_provider_status(self) -> dict:
        """Read configured provider status without making billable model calls."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/api/v1/providers/status")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(self._extract_error(exc.response)) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Could not reach the provider status API: {exc}") from exc

    def test_provider(self, provider: str) -> dict:
        """Run an explicit provider connection test. This may consume provider credits."""
        payload = {"provider": provider.lower().replace(" (local)", "")}
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/api/v1/providers/test",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(self._extract_error(exc.response)) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Could not reach the provider test API: {exc}") from exc

    def route_report(self, report_id: str, provider: str | None = None) -> dict:
        """Run supervisor routing for a confirmed report."""
        payload = {
            "report_id": report_id,
            "preferred_provider": (
                provider.lower().replace(" (local)", "") if provider else None
            ),
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/v1/analysis/route",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(self._extract_error(exc.response)) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Could not reach the routing API: {exc}") from exc

    def set_manual_route(self, report_id: str, report_type: str) -> dict:
        """Save a user-selected report route."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/v1/analysis/{report_id}/manual-route",
                    json={"report_type": report_type},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(self._extract_error(exc.response)) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Could not reach the manual routing API: {exc}") from exc

    def explain_report(
        self,
        report_id: str,
        language: str,
        provider: str | None = None,
    ) -> dict:
        """Run the specialized report explanation agent selected by Phase 4."""
        payload = {
            "report_id": report_id,
            "language": language.lower(),
            "preferred_provider": (
                provider.lower().replace(" (local)", "") if provider else None
            ),
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/v1/analysis/explain",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(self._extract_error(exc.response)) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Could not reach the report explanation API: {exc}") from exc
