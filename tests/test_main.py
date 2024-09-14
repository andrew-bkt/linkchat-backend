# backend/tests/test_main.py

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/api/v1/")
    assert response.status_code == 404  # Adjust based on your routes