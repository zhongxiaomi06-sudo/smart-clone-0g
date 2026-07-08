from __future__ import annotations

import json
from pathlib import Path

from smart_avatar.audit import AuditService
from smart_avatar.credentials import CredentialService
from smart_avatar.domain import (
    CredentialCreateRequest,
    MemoryCard,
    SkillRunRequest,
    ToolCallRequest,
)
from smart_avatar.mcp import McpGateway
from smart_avatar.models import DryRunModelClient
from smart_avatar.permissions import PermissionService
from smart_avatar.privacy import PrivacyProjector
from smart_avatar.skills import SkillRegistry
from smart_avatar.storage import SQLiteStore


def write_test_skill(skills_dir: Path) -> None:
    skill_dir = skills_dir / "test_skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "name": "test_skill",
                "display_name": "测试 Skill",
                "type": "skill",
                "description": "A test skill.",
                "triggers": ["测试"],
                "entry": {"kind": "prompt_template", "prompt_path": "prompt.md"},
                "memory_scope": {
                    "default_time_range": None,
                    "allowed_fields": ["event_summary", "insight"],
                    "requires_user_confirm": True,
                },
                "permissions": ["memory:read:desensitized"],
                "output_schema": ["result"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (skill_dir / "prompt.md").write_text(
        "intent=$user_intent\nmemories=$memory_cards\nargs=$arguments",
        encoding="utf-8",
    )


def build_runtime(tmp_path: Path) -> tuple[SkillRegistry, SQLiteStore, PermissionService]:
    skills_dir = tmp_path / "skills"
    write_test_skill(skills_dir)
    store = SQLiteStore(tmp_path / "app.db")
    store.add_memory(
        MemoryCard(
            event_summary="用户在会议中坚持表达自己的判断。",
            insight="用户希望观点被充分理解。",
            tags=["工作", "沟通"],
        )
    )
    audit = AuditService(store)
    permissions = PermissionService(store)
    registry = SkillRegistry(
        skills_dir=skills_dir,
        store=store,
        permissions=permissions,
        audit=audit,
        model_client=DryRunModelClient(),
        require_confirmation=True,
    )
    return registry, store, permissions


def build_registry(tmp_path: Path) -> SkillRegistry:
    registry, _, _ = build_runtime(tmp_path)
    return registry


def test_skill_registry_loads_manifest(tmp_path: Path) -> None:
    registry = build_registry(tmp_path)

    skills = registry.list()

    assert [skill.name for skill in skills] == ["test_skill"]


def test_skill_requires_confirmation(tmp_path: Path) -> None:
    registry = build_registry(tmp_path)

    result = registry.run("test_skill", SkillRunRequest(user_intent="帮我测试"))

    assert result.status == "permission_required"
    assert result.missing_permissions == ["memory:read:desensitized"]


def test_skill_runs_after_user_confirmation(tmp_path: Path) -> None:
    registry = build_registry(tmp_path)

    result = registry.run(
        "test_skill",
        SkillRunRequest(user_intent="测试会议记忆", user_confirmed=True),
    )

    assert result.status == "completed"
    assert result.used_context
    assert "prepared_prompt" in result.result


def test_skill_runs_with_permission_token(tmp_path: Path) -> None:
    registry, _, permissions = build_runtime(tmp_path)
    grant = permissions.grant("test_skill", ["memory:read:desensitized"])

    result = registry.run(
        "test_skill",
        SkillRunRequest(user_intent="测试会议记忆", permission_token=grant.id),
    )

    assert result.status == "completed"
    assert result.used_context


def test_privacy_projector_limits_memory_fields() -> None:
    projector = PrivacyProjector()
    card = MemoryCard(
        event_summary="用户完成一次重要讨论。",
        insight="用户更重视被理解。",
        entities={"people": ["同事A"]},
    )

    projected = projector.project_memory(card, ["event_summary"])

    assert projected == {"id": card.id, "event_summary": "用户完成一次重要讨论。"}


def test_credential_hash_is_stable(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "app.db")
    audit = AuditService(store)
    credentials = CredentialService(store, audit)

    first = credentials.create_hash_credential(
        CredentialCreateRequest(
            subject_type="memory",
            subject_id="mem_1",
            payload={"b": 2, "a": 1},
        )
    )
    second = credentials.create_hash_credential(
        CredentialCreateRequest(
            subject_type="memory",
            subject_id="mem_1",
            payload={"a": 1, "b": 2},
        )
    )

    assert first.digest == second.digest


def test_disabled_tool_does_not_run(tmp_path: Path) -> None:
    tools_dir = tmp_path / "tools"
    tool_dir = tools_dir / "calendar"
    tool_dir.mkdir(parents=True)
    (tool_dir / "tool.json").write_text(
        json.dumps(
            {
                "name": "calendar",
                "display_name": "日历",
                "description": "Calendar tool.",
                "enabled": False,
                "entry": {"kind": "dry_run"},
                "permissions": ["tool:calendar:read"],
                "input_schema": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    store = SQLiteStore(tmp_path / "app.db")
    audit = AuditService(store)
    permissions = PermissionService(store)
    gateway = McpGateway(tools_dir=tools_dir, audit=audit, permissions=permissions)

    result = gateway.call(ToolCallRequest(tool_name="calendar"))

    assert result.status == "not_configured"
