from fastapi.testclient import TestClient

from services.api.app.main import app


def test_health_reports_local_service() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["mode"] == "local"


def test_bootstrap_demo_has_exact_feeder_path() -> None:
    with TestClient(app) as client:
        response = client.get("/api/bootstrap/demo")
    assert response.status_code == 200
    graph = response.json()["graph"]
    assert graph["feeder_paths"] == [
        {
            "feeder_equipment_id": "feeder_01",
            "source_equipment_id": "source_grid",
            "equipment_path": [
                "source_grid",
                "transformer_01",
                "bus_a",
                "breaker_01",
                "ct_01",
                "feeder_01",
            ],
            "confidence": 1.0,
            "active": True,
        }
    ]
    assert "<svg" in response.json()["svg"]
