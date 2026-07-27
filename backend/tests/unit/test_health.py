from app.core import constants

def test_read_root(client) -> None:
    """
    Test that the root endpoint returns a welcome message and doc info.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["api_version"] == constants.VERSION
    assert "docs_url" in data

def test_get_health(client) -> None:
    """
    Test that the health endpoint returns service name, version, and healthy status.
    """
    response = client.get(f"{constants.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == constants.PROJECT_NAME
    assert data["version"] == constants.VERSION
