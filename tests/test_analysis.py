from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analysis_returns_markets():
    payload = {
        "home": {"name": "Home FC", "avg_goals_scored": 1.6, "avg_goals_conceded": 0.9, "form_points_per_game": 2.0},
        "away": {"name": "Away FC", "avg_goals_scored": 1.1, "avg_goals_conceded": 1.3, "form_points_per_game": 1.2}
    }
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["markets"]) == 5
    assert body["expected_home_goals"] > 0
