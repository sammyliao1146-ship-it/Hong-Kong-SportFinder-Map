from fastapi.testclient import TestClient

from backend.app.data.sources import CATEGORIES
from backend.app.models.venue import Availability, AvailabilityStatus
from backend.tests.conftest import make_settings


def test_unloaded_data_is_not_reported_as_zero_venues(make_app):
    with TestClient(make_app()) as client:
        assert client.get("/api/v1/health").status_code == 200
        data = client.get("/api/v1/venues").json()
        assert data["data_status"] == "not_synced"
        assert data["total"] is None
        assert data["items"] == []


def test_research_counts_are_not_exposed_as_unique_total(make_app):
    with TestClient(make_app()) as client:
        data = client.get("/api/v1/sources").json()
        assert len(data["sources"]) == len(CATEGORIES)
        assert data["unique_venue_total"] is None
        assert data["booking_sync"] == "not_connected"
        assert all(s["count_provenance"] == "raw_layer_records" for s in data["sources"])


def test_no_capacity_data_means_unknown():
    data = Availability()
    assert data.status == AvailabilityStatus.UNKNOWN
    assert data.remaining is None


def test_chat_without_credentials_does_not_call_provider(make_app):
    with TestClient(make_app()) as client:
        assert client.post("/api/v1/assistant/chat", json={"message": "hi"}).status_code == 503
        assert client.post("/api/v1/assistant/chat", json={"message": "   "}).status_code == 422


def test_chat_uses_shared_data_service(make_app, monkeypatch):
    from backend.app.routers import assistant

    async def fake_run(message, **kwargs):
        assert message == "附近有什么场所？"
        assert kwargs["access"].venues is app.state.container.venues
        return "场所数据尚未接入，余量未知。"

    monkeypatch.setattr(assistant, "run_sports_assistant", fake_run)
    app = make_app(make_settings("test-key", "test-model"))
    with TestClient(app) as client:
        response = client.post("/api/v1/assistant/chat", json={"message": "附近有什么场所？"})
        assert response.status_code == 200
        assert response.json() == {"answer": "场所数据尚未接入，余量未知。", "model": "test-model"}


def test_chat_is_rate_limited(make_app, monkeypatch):
    from backend.app.routers import assistant

    async def fake_run(message, **kwargs):
        return "ok"

    monkeypatch.setattr(assistant, "run_sports_assistant", fake_run)
    app = make_app(make_settings("k", "m", chat_rate_limit=2, chat_rate_window_seconds=60))
    with TestClient(app) as client:
        codes = [client.post("/api/v1/assistant/chat", json={"message": "hi"}).status_code for _ in range(3)]
        assert codes == [200, 200, 429]
        assert client.get("/api/v1/health").headers["x-request-id"]
