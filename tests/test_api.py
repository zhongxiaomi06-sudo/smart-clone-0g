from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from smart_avatar.app import create_app
from smart_avatar.config import ApiConfig, AppConfig, RateLimitConfig, SecurityConfig


def build_config(tmp_path: Path, *, api_key_enabled: bool = False) -> AppConfig:
    return AppConfig(
        database_path=str(tmp_path / "app.db"),
        skills_dir=str(tmp_path / "skills"),
        tools_dir=str(tmp_path / "tools"),
        api=ApiConfig(prefix="/api/v1", legacy_prefix_enabled=True),
        security=SecurityConfig(api_key_enabled=api_key_enabled),
        rate_limit=RateLimitConfig(enabled=False),
    )


def test_health_includes_request_id(tmp_path: Path) -> None:
    client = TestClient(create_app(build_config(tmp_path)))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_web_app_root_is_served(tmp_path: Path) -> None:
    config = build_config(tmp_path)
    config.web_dir = "web"
    client = TestClient(create_app(config))

    response = client.get("/")

    assert response.status_code == 200
    assert "智慧分身" in response.text


def test_versioned_and_legacy_memory_routes_work(tmp_path: Path) -> None:
    client = TestClient(create_app(build_config(tmp_path)))
    payload = {"event_summary": "用户完成一次商业级框架优化。"}

    created = client.post("/api/v1/memories", json=payload)
    legacy_list = client.get("/api/memories")

    assert created.status_code == 200
    assert legacy_list.status_code == 200
    assert legacy_list.json()[0]["event_summary"] == payload["event_summary"]


def test_api_key_blocks_private_routes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SMART_AVATAR_API_KEY", "secret")
    client = TestClient(create_app(build_config(tmp_path, api_key_enabled=True)))

    public_page = client.get("/")
    unauthorized = client.get("/api/v1/memories")
    authorized = client.get("/api/v1/memories", headers={"x-api-key": "secret"})

    assert public_page.status_code == 200
    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "unauthorized"
    assert authorized.status_code == 200
