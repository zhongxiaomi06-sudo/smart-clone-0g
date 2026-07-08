from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    provider: str = "dry_run"
    default_model: str = "dry-run"
    base_url: str | None = None
    api_key_env: str | None = None
    timeout_seconds: int = 60


class TranscriptionConfig(BaseModel):
    """语音转写配置。遵循设计文档 5.1:本地优先,可在端侧完成。"""

    provider: str = "dry_run"
    model_size: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    default_language: str = "zh"
    auto_extract: bool = True
    max_cards_per_recording: int = 5
    auto_delete_after_days: int | None = None


class PrivacyConfig(BaseModel):
    require_skill_confirmation: bool = True
    allow_raw_memory_to_tools: bool = False
    audit_all_tool_calls: bool = True


class SecurityConfig(BaseModel):
    api_key_enabled: bool = False
    api_key_env: str = "SMART_AVATAR_API_KEY"
    public_paths: list[str] = Field(
        default_factory=lambda: ["/", "/static", "/health", "/docs", "/openapi.json"]
    )


class RateLimitConfig(BaseModel):
    enabled: bool = True
    requests_per_minute: int = 120


class ApiConfig(BaseModel):
    prefix: str = "/api/v1"
    legacy_prefix_enabled: bool = True


class AppConfig(BaseModel):
    app_name: str = "智慧分身"
    database_path: str = "data/smart_avatar.db"
    skills_dir: str = "skills"
    tools_dir: str = "tools"
    web_dir: str = "web"
    recordings_dir: str = "data/recordings"
    api: ApiConfig = Field(default_factory=ApiConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project_root() / path


def load_config(config_path: str | None = None) -> AppConfig:
    path_value = config_path or os.getenv("SMART_AVATAR_CONFIG", "config/app.json")
    path = resolve_path(path_value)
    if not path.exists():
        return AppConfig()
    with path.open("r", encoding="utf-8") as config_file:
        return AppConfig.model_validate(json.load(config_file))
