from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers["x-request-id"]


def test_mutation_requires_json():
    r = client.post("/api/v1/health", content="x", headers={"content-type": "text/plain"})
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "unsupported_media_type"


def test_foreign_origin_is_rejected():
    r = client.post("/api/v1/health", json={}, headers={"origin": "https://evil.example"})
    assert r.status_code == 403


def test_tailnet_origin_is_allowed_past_guard():
    r = client.post("/api/v1/health", json={}, headers={"origin": "https://mac.tail1234.ts.net"})
    assert r.status_code == 405


def test_unknown_host_is_rejected():
    r = client.get("/api/v1/health", headers={"host": "attacker.example"})
    assert r.status_code == 400
