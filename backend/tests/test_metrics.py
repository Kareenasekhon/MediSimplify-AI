from __future__ import annotations

from app.services.metrics_service import metrics_service


def test_metrics_endpoint_returns_expected_shape(client):
    metrics_service.reset_for_tests()
    client.get("/")
    response = client.get("/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_requests"] >= 1
    assert payload["successful_requests"] >= 1
    assert "average_response_ms" in payload
    assert "request_categories" in payload
    assert "provider_usage" in payload


def test_metrics_tracks_failed_requests(client):
    metrics_service.reset_for_tests()
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    payload = client.get("/metrics").json()
    assert payload["failed_requests"] >= 1


def test_versioned_metrics_alias(client):
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
