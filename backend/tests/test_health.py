"""Tests for backend health and unimplemented voice integration status."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture
def client_without_credentials():
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        elevenlabs_api_key=None,
        elevenlabs_voice_id=None,
    )
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_application_starts_without_elevenlabs_credentials(
    client_without_credentials: TestClient,
) -> None:
    response = client_without_credentials.get("/api/health")

    assert response.status_code == 200


def test_health_endpoint(client_without_credentials: TestClient) -> None:
    response = client_without_credentials.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "knighthacks-backend",
    }


def test_voice_status_without_credentials_and_without_external_calls(
    client_without_credentials: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_external_request(*args: object, **kwargs: object) -> None:
        pytest.fail("The placeholder voice status endpoint must not make HTTP requests")

    monkeypatch.setattr(httpx.AsyncClient, "request", reject_external_request)

    response = client_without_credentials.get("/api/voice/status")

    assert response.status_code == 200
    assert response.json() == {
        "configured": False,
        "message": "ElevenLabs integration not configured yet",
    }


def test_voice_status_does_not_expose_configured_credentials() -> None:
    settings = Settings(
        _env_file=None,
        elevenlabs_api_key="test-api-secret",
        elevenlabs_voice_id="test-voice-secret",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as test_client:
            response = test_client.get("/api/voice/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["configured"] is True
    assert "test-api-secret" not in response.text
    assert "test-voice-secret" not in response.text
