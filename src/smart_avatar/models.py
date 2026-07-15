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
        """调用 OpenAI 兼容接口。失败时抛异常,由调用方决定降级策略。"""
        import urllib.request  # noqa: PLC0415

        if not self.api_key:
            raise RuntimeError(
                f"API Key 未设置。请在环境变量 {self.config.api_key_env} 中配置。"
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
                # 部分服务商前置 Cloudflare(如 Gonka Router),
                # 默认 Python-urllib UA 会触发 403(1010),显式声明 UA 规避
                "User-Agent": "smart-avatar/0.1 (+https://github.com/zhongxiaomi06-sudo/smart-clone-0g)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="ignore")
            except Exception:  # noqa: BLE001
                pass
            raise RuntimeError(f"模型调用失败(HTTP {exc.code}):{detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"模型调用失败(网络错误):{exc.reason}") from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"模型调用失败:{exc}") from exc


@dataclass
class ZeroGRouterClient:
    """0G Compute Router API 客户端。

    通过 0G 官方 Router 调用去中心化算力网络中的模型。
    端点: https://router-api.0g.ai/v1 (主网) 或测试网等效地址。
    认证: Bearer API Key,在 pc.0g.ai 连接钱包并充值后创建。
    """

    config: ModelConfig
    model_name: str = ""
    base_url: str = "https://router-api.0g.ai/v1"
    api_key: str = field(default="", repr=False)
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        self.model_name = self.config.default_model
        self.base_url = self.config.base_url or "https://router-api.0g.ai/v1"
        self.timeout_seconds = self.config.timeout_seconds
        if self.config.api_key_env:
            self.api_key = os.getenv(self.config.api_key_env, "")

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        """调用 0G Router API。失败时抛异常,由调用方决定降级策略。"""
        import urllib.request  # noqa: PLC0415

        if not self.api_key:
            raise RuntimeError(
                f"0G Router API Key 未设置。请在环境变量 {self.config.api_key_env} 中配置。"
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
                # 部分服务商前置 Cloudflare(如 Gonka Router),
                # 默认 Python-urllib UA 会触发 403(1010),显式声明 UA 规避
                "User-Agent": "smart-avatar/0.1 (+https://github.com/zhongxiaomi06-sudo/smart-clone-0g)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="ignore")
            except Exception:  # noqa: BLE001
                pass
            raise RuntimeError(f"0G Router 调用失败(HTTP {exc.code}):{detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"0G Router 调用失败(网络错误):{exc.reason}") from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"0G Router 调用失败:{exc}") from exc


@dataclass
class ZeroGVerifiableClient:
    """0G Compute Network 可验证推理客户端。

    通过 python-0g SDK 直接调用 Provider,支持 TEE 可验证推理。
    每次响应包含链上 chatID,可用于验证推理完整性与来源。
    优先选择 0GM-1.0-35B-A3B 自研模型。
    """

    config: ModelConfig
    _a0g_client: Any = field(default=None, repr=False)

    def _get_a0g(self):
        if self._a0g_client is None:
            try:
                from a0g.base import A0G  # type: ignore[import-not-found]
            except ImportError as exc:
                raise RuntimeError(
                    "python-0g 未安装。请执行 pip install python-0g 安装 0G SDK。"
                ) from exc
            self._a0g_client = A0G()
        return self._a0g_client

    def _select_service(self, services: list[Any]) -> Any:
        """优先选择 0GM-1.0-35B-A3B,否则回退到第一个可用服务。"""
        prefer = (self.config.zg_prefer_model or "0GM-1.0-35B-A3B").lower()
        for svc in services:
            model_name = getattr(svc, "model", "") or ""
            if prefer in model_name.lower():
                return svc
        if services:
            return services[0]
        raise RuntimeError("0G Compute Network 上没有可用服务。")

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        a0g = self._get_a0g()
        services = a0g.get_all_services()
        service = self._select_service(services)
        client = a0g.get_openai_client(service.provider)
        resp = client.chat.completions.create(
            model=service.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content

    def generate_with_proof(
        self, *, system_prompt: str, user_prompt: str
    ) -> dict[str, Any]:
        """返回响应内容 + 可验证推理元数据(chatID、模型、Provider)。"""
        a0g = self._get_a0g()
        services = a0g.get_all_services()
        service = self._select_service(services)
        client = a0g.get_openai_client(service.provider)
        resp = client.chat.completions.create(
            model=service.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = resp.choices[0].message.content
        chat_id = getattr(resp, "id", None) or getattr(resp, "chatID", None)
        return {
            "content": content,
            "chat_id": chat_id,
            "model": service.model,
            "provider": service.provider,
            "verifiable": True,
            "network": "0G Compute Network",
        }


def create_model_client(config: ModelConfig) -> ModelClient:
    if config.provider == "dry_run":
        return DryRunModelClient(model_name=config.default_model)
    if config.provider in ("openai", "openai_compatible", "deepseek", "qwen", "moonshot"):
        return OpenAICompatibleClient(config=config)
    if config.provider == "0g":
        return ZeroGRouterClient(config=config)
    if config.provider == "0g_verifiable":
        return ZeroGVerifiableClient(config=config)
    return ProviderPlaceholderClient(config=config)
