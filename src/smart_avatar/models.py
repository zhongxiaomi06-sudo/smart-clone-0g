from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .config import ModelConfig


class ModelClient(Protocol):
    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        ...


@dataclass(frozen=True)
class DryRunModelClient:
    model_name: str = "dry-run"

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        return (
            f"[dry-run:{self.model_name}] Model provider is not configured. "
            "The framework prepared prompts and context successfully."
        )


@dataclass(frozen=True)
class ProviderPlaceholderClient:
    config: ModelConfig

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        return (
            f"[provider-placeholder:{self.config.provider}] "
            "This model provider is declared in config but no adapter is implemented yet."
        )


def create_model_client(config: ModelConfig) -> ModelClient:
    if config.provider == "dry_run":
        return DryRunModelClient(model_name=config.default_model)
    return ProviderPlaceholderClient(config=config)
