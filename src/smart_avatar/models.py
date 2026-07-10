from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

from .config import ModelConfig


class ModelClient(Protocol):
    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        ...


@dataclass(frozen=True)
class DryRunModelClient:
    model_name: str = "dry-run"

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        return (
            f"[dry-run:{self.model_name}] 模型未配置真实推理后端。"
            "框架已成功组装提示词和上下文,但未调用真实大模型。"
            "请在 config/app.json 中配置 model.provider 和 model.api_key_env 后使用。"
        )


@dataclass(frozen=True)
class ProviderPlaceholderClient:
    config: ModelConfig

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        return (
            f"[provider-placeholder:{self.config.provider}] "
            "该模型提供商已在配置中声明,但尚未实现适配器。"
        )


@dataclass
class OpenAICompatibleClient:
    """OpenAI 兼容 API 适配器。

    支持所有兼容 OpenAI Chat Completions 接口的服务商:
    OpenAI 官方、DeepSeek、通义千问、Moonshot、本地 vLLM/Ollama 等。
    遵循设计文档 9:推理层可配置云端大模型。
    """

    config: ModelConfig
    model_name: str = ""
    base_url: str = "https://api.openai.com/v1"
    api_key: str = field(default="", repr=False)
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        self.model_name = self.config.default_model
        self.base_url = self.config.base_url or "https://api.openai.com/v1"
        self.timeout_seconds = self.config.timeout_seconds
        if self.config.api_key_env:
            self.api_key = os.getenv(self.config.api_key_env, "")

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        try:
            import urllib.request  # noqa: PLC0415
        except ImportError:
            return "[error] urllib 不可用"

        if not self.api_key:
            return (
                f"[error] API Key 未设置。请在环境变量 {self.config.api_key_env} 中配置。"
            )

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            return f"[error] 模型调用失败:{exc}"


def create_model_client(config: ModelConfig) -> ModelClient:
    if config.provider == "dry_run":
        return DryRunModelClient(model_name=config.default_model)
    if config.provider in ("openai", "openai_compatible", "deepseek", "qwen", "moonshot"):
        return OpenAICompatibleClient(config=config)
    return ProviderPlaceholderClient(config=config)
