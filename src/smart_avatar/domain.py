from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class Emotion(BaseModel):
    label: str = "unknown"
    intensity: float | None = None


class MemoryCard(BaseModel):
    id: str = Field(default_factory=lambda: new_id("mem"))
    time_range: str | None = None
    event_summary: str
    emotion: Emotion | None = None
    insight: str | None = None
    personality_signals: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    entities: dict[str, list[str]] = Field(default_factory=dict)
    privacy_level: str = "desensitized"
    source_type: str = "manual"
    created_at: str = Field(default_factory=utc_now)


class StateCard(BaseModel):
    id: str = Field(default_factory=lambda: new_id("state"))
    date: str
    sleep_summary: str | None = None
    body_signals: list[str] = Field(default_factory=list)
    environment_signals: list[str] = Field(default_factory=list)
    self_report: dict[str, Any] = Field(default_factory=dict)
    possible_links: list[str] = Field(default_factory=list)
    risk_level: str = "observation_only"
    created_at: str = Field(default_factory=utc_now)


class Citation(BaseModel):
    source_type: Literal["memory", "state", "skill", "tool"]
    source_id: str
    summary: str | None = None


class MemoryQuery(BaseModel):
    query: str
    time_range: str | None = None
    tags: list[str] = Field(default_factory=list)
    limit: int = 8


class MemoryQueryResponse(BaseModel):
    memory_cards: list[MemoryCard]
    citations: list[Citation]


class PermissionGrant(BaseModel):
    id: str = Field(default_factory=lambda: new_id("perm"))
    target: str
    scope: list[str]
    expires_at: str | None = None
    revoked_at: str | None = None
    created_at: str = Field(default_factory=utc_now)


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: new_id("audit"))
    event_type: str
    target: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class SkillMemoryScope(BaseModel):
    default_time_range: str | None = None
    allowed_fields: list[str] = Field(default_factory=list)
    requires_user_confirm: bool = True


class SkillEntry(BaseModel):
    kind: Literal["prompt_template", "internal", "mcp_tool"] = "prompt_template"
    handler: str | None = None
    prompt_path: str | None = None


class SkillManifest(BaseModel):
    name: str
    display_name: str
    type: Literal["skill"] = "skill"
    version: str = "0.1.0"
    description: str
    triggers: list[str] = Field(default_factory=list)
    entry: SkillEntry = Field(default_factory=SkillEntry)
    memory_scope: SkillMemoryScope = Field(default_factory=SkillMemoryScope)
    permissions: list[str] = Field(default_factory=list)
    output_schema: list[str] = Field(default_factory=list)


class SkillRunRequest(BaseModel):
    user_intent: str
    memory_query: MemoryQuery | None = None
    context_refs: list[str] = Field(default_factory=list)
    permission_token: str | None = None
    user_confirmed: bool = False
    arguments: dict[str, Any] = Field(default_factory=dict)


class SkillRunResult(BaseModel):
    skill_name: str
    status: Literal["prepared", "completed", "permission_required", "not_found", "error"]
    result: dict[str, Any] = Field(default_factory=dict)
    used_context: list[Citation] = Field(default_factory=list)
    missing_permissions: list[str] = Field(default_factory=list)
    audit_id: str | None = None


class ChatRequest(BaseModel):
    message: str
    skill_name: str | None = None
    permission_token: str | None = None
    user_confirmed: bool = False
    limit: int = 8


class ChatResponse(BaseModel):
    action: Literal["memory_answer", "skill_run", "permission_required", "clarify"]
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    skill_result: SkillRunResult | None = None


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    permission_token: str | None = None


class ToolCallResult(BaseModel):
    tool_name: str
    status: Literal["completed", "permission_required", "not_configured", "error"]
    result: dict[str, Any] = Field(default_factory=dict)
    audit_id: str | None = None


class ToolEntry(BaseModel):
    kind: Literal["dry_run", "mcp_server", "internal"] = "dry_run"
    handler: str | None = None


class ToolManifest(BaseModel):
    name: str
    display_name: str
    description: str
    enabled: bool = False
    entry: ToolEntry = Field(default_factory=ToolEntry)
    permissions: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)


class CredentialCreateRequest(BaseModel):
    subject_type: str
    subject_id: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class CredentialRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("cred"))
    subject_type: str
    subject_id: str
    hash_algorithm: str = "sha256"
    digest: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    anchor_status: Literal["local", "submitted", "anchored"] = "local"
    created_at: str = Field(default_factory=utc_now)


class AudioRecording(BaseModel):
    """端侧录音记录。原始音频默认只保留在本地,不上传云端。

    source_type=local_transcript 的记忆卡片由录音转写并脱敏提炼后生成。
    """

    id: str = Field(default_factory=lambda: new_id("rec"))
    file_name: str
    storage_path: str
    mime_type: str = "audio/webm"
    duration_seconds: float | None = None
    size_bytes: int = 0
    recorded_at: str = Field(default_factory=utc_now)
    transcript: str | None = None
    transcript_language: str | None = None
    transcript_status: Literal["pending", "running", "completed", "failed"] = "pending"
    transcript_error: str | None = None
    transcript_provider: str | None = None
    extracted_memory_ids: list[str] = Field(default_factory=list)
    auto_delete_after_days: int | None = None
    created_at: str = Field(default_factory=utc_now)


class TranscriptionRequest(BaseModel):
    language: str | None = None
    auto_extract: bool = True


class TranscriptionResult(BaseModel):
    recording_id: str
    status: Literal["pending", "running", "completed", "failed"]
    transcript: str | None = None
    language: str | None = None
    provider: str | None = None
    error: str | None = None
    extracted_memory_ids: list[str] = Field(default_factory=list)


class MemoryExtractionRequest(BaseModel):
    """从转写文本提炼记忆卡片的请求。

    遵循设计文档 11.1 提示词:少发挥、多提炼、强脱敏。
    """

    recording_id: str
    language: str | None = None
    max_cards: int = 5
    auto_desensitize: bool = True


class MemoryExtractionResult(BaseModel):
    recording_id: str
    memory_cards: list[MemoryCard] = Field(default_factory=list)
    provider: str | None = None
    error: str | None = None
