from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_api_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_single_syntax_error():
    response = client.post("/api/v1/verify", json={"email": "bad@@example.com", "smtp_check": False})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "syntax_error"
    assert body["recommended_action"] == "correct_typo_first"


def test_api_bulk_job_created():
    response = client.post("/api/v1/verify/bulk", json={"emails": ["bad@@example.com"]})
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"].startswith("job_")
