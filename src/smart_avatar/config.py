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
    # 0G Compute Network 扩展字段
    zg_rpc_url_env: str | None = None  # A0G_RPC_URL
    zg_private_key_env: str | None = None  # A0G_PRIVATE_KEY
    zg_prefer_model: str | None = None  # 优先模型名,如 0GM-1.0-35B-A3B
    zg_network: str = "testnet"  # 0G 网络:testnet / mainnet


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


class EmbeddingConfig(BaseModel):
    """嵌入模型配置。遵循设计文档 5.2:本地嵌入模型将事件和洞察转为向量。"""

    provider: str = "dry_run"
    model_name: str = "BAAI/bge-small-zh-v1.5"
    dimension: int = 256


class PrivacyConfig(BaseModel):
    require_skill_confirmation: bool = True
    allow_raw_memory_to_tools: bool = False
    audit_all_tool_calls: bool = True


class SecurityConfig(BaseModel):
    api_key_enabled: bool = False  # 保持默认 False（开发模式）
    api_key_env: str = "SMART_AVATAR_API_KEY"
    jwt_secret_env: str = "SMART_AVATAR_JWT_SECRET"
    jwt_expire_minutes: int = 1440  # 24 小时
    cors_origins: list[str] = Field(default_factory=list)  # 空=不允许跨域
    max_upload_size_mb: int = 50
    public_paths: list[str] = Field(
        default_factory=lambda: ["/", "/static", "/health", "/docs", "/openapi.json", "/api/v1/auth/register", "/api/v1/auth/login", "/auth/register", "/auth/login"]
    )


class EnvironmentConfig(BaseModel):
    """环境配置。生产环境强制开启认证。"""

    environment: str = "dev"  # dev / prod
    database_url: str | None = None  # PostgreSQL 连接 URL（可选）
    backup_dir: str = "data/backups"
    log_level: str = "INFO"


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
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return project_root() / path


def _load_env() -> None:
    """加载项目根目录的 .env 文件,将变量注入 os.environ。"""
    env_path = project_root() / ".env"
    if not env_path.exists():
        return
    with env_path.open("r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def load_config(config_path: str | None = None) -> AppConfig:
    _load_env()
    path_value = config_path or os.getenv("SMART_AVATAR_CONFIG", "config/app.json")
    path = resolve_path(path_value)
    if not path.exists():
        config = AppConfig()
    else:
        with path.open("r", encoding="utf-8") as config_file:
            config = AppConfig.model_validate(json.load(config_file))

    # 生产环境强制开启认证
    if config.environment.environment == "prod":
        config.security.api_key_enabled = True
        if config.environment.log_level == "DEBUG":
            config.environment.log_level = "INFO"  # 生产环境不允许 DEBUG

    return config
