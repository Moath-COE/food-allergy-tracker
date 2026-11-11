import pytest
from fastapi.testclient import TestClient

from hassas.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())
