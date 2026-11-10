# tests/conftest.py
import pytest
from fastapi.testclient import TestClient

from food_allergy_tracker.deps import get_item_service
from food_allergy_tracker.main import create_app
from food_allergy_tracker.services.items import ItemService


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_item_service] = lambda: service
    service = ItemService()  # fresh, empty store for every test
    return TestClient(app)