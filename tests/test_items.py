# tests/test_items.py
def test_create_and_get_item(client):
    response = client.post("/items", json={"name": "Pen", "price": 2.5})
    assert response.status_code == 201
    item = response.json()
    assert item == {"id": 1, "name": "Pen", "price": 2.5}

    response = client.get(f"/items/{item['id']}")
    assert response.status_code == 200


def test_missing_item_returns_404(client):
    assert client.get("/items/999").status_code == 404


def test_invalid_price_is_rejected(client):
    response = client.post("/items", json={"name": "Pen", "price": -1})
    assert response.status_code == 422