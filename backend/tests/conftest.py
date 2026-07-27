import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client() -> TestClient:
    """
    Fixture providing a test client for calling API endpoints.
    """
    with TestClient(app) as c:
        yield c
