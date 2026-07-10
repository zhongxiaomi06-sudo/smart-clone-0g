from __future__ import annotations

import json
import logging
from pathlib import Path
from string import Template

from .audit import AuditService
from .domain import (
    Citation,
    MemoryQuery,
    SkillManifest,
    SkillRunRequest,
    SkillRunResult,
)
from .models import ModelClient
from .permissions import PermissionService
from .privacy import PrivacyProjector
from .storage import SQLiteStore

logger = logging.getLogger("smart_avatar.skills")


class SkillRegistry:
    def __init__(
        self,
        *,
        skills_dir: Path,
        store: SQLiteStore,
        permissions: PermissionService,
        audit: AuditService,
        model_client: ModelClient,
        require_confirmation: bool,
    ) -> None:
        self.skills_dir = skills_dir
        self.store = store
        self.permissions = permissions
        self.audit = audit
        self.model_client = model_client
        self.require_confirmation = require_confirmation
        self.privacy = PrivacyProjector()
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[SkillManifest]:
        manifests: list[SkillManifest] = []
        for manifest_path in self.skills_dir.glob("*/skill.json"):
            manifests.append(self._load_manifest(manifest_path))
        return sorted(manifests, key=lambda manifest: manifest.name)

    def get(self, name: str) -> SkillManifest | None:
        manifest_path = self.skills_dir / name / "skill.json"
        if not manifest_path.exists():
            return None
        return self._load_manifest(manifest_path)

    def match(self, message: str) -> SkillManifest | None:
        normalized = message.lower()
        for manifest in self.list():
            if any(trigger.lower() in normalized for trigger in manifest.triggers):
                return manifest
        return None

    def run(self, name: str, request: SkillRunRequest) -> SkillRunResult:
        manifest = self.get(name)
        if manifest is None:
            return SkillRunResult(skill_name=name, status="not_found")

        # 开始执行技能
        logger.info("skill.run.start", extra={"skill": name})

        missing_permissions = self._missing_permissions(manifest, request)
        if missing_permissions:
            # 权限不足，记录警告
            logger.warning(
                "skill.permission_required",
                extra={"skill": name, "missing": missing_permissions},
            )
            audit = self.audit.record(
                "skill.permission_required",
                manifest.name,
                {"missing_permissions": missing_permissions},
            )
            return SkillRunResult(
                skill_name=manifest.name,
                status="permission_required",
                missing_permissions=missing_permissions,
                audit_id=audit.id,
            )

        memory_query = request.memory_query or MemoryQuery(
            query=request.user_intent,
            time_range=manifest.memory_scope.default_time_range,
        )
        memories = self.store.query_memories(memory_query)
        citations = [
            Citation(source_type="memory", source_id=card.id, summary=card.event_summary)
            for card in memories
        ]

        prompt = self._render_prompt(manifest, request, memories)
        # 调用模型生成输出，捕获异常以便记录审计与日志
        try:
            model_output = self.model_client.generate(
                system_prompt=manifest.description,
                user_prompt=prompt,
            )
        except Exception as exc:
            logger.error(
                "skill.model_error",
                extra={"skill": name, "error": str(exc)},
            )
            audit = self.audit.record(
                "skill.error",
                manifest.name,
                {"error": str(exc), "memory_ids": [card.id for card in memories]},
            )
            return SkillRunResult(
                skill_name=manifest.name,
                status="error",
                result={"error": str(exc)},
                used_context=citations,
                audit_id=audit.id,
            )

        audit = self.audit.record(
            "skill.run",
            manifest.name,
            {
                "memory_ids": [card.id for card in memories],
                "permissions": manifest.permissions,
            },
        )
        # 成功完成
        logger.info(
            "skill.run.complete",
            extra={"skill": name, "memory_count": len(memories)},
        )
        return SkillRunResult(
            skill_name=manifest.name,
            status="completed",
            result={
                "model_output": model_output,
                "prepared_prompt": prompt,
                "output_schema": manifest.output_schema,
            },
            used_context=citations,
            audit_id=audit.id,
        )

    def _load_manifest(self, manifest_path: Path) -> SkillManifest:
        with manifest_path.open("r", encoding="utf-8") as file:
            return SkillManifest.model_validate(json.load(file))

    def _missing_permissions(
        self,
        manifest: SkillManifest,
        request: SkillRunRequest,
    ) -> list[str]:
        if not manifest.permissions:
            return []
        if not self.require_confirmation:
            return []
        if request.user_confirmed:
            return []
        if self.permissions.has_scope(request.permission_token, manifest.permissions):
            return []
        return manifest.permissions

    def _render_prompt(
        self,
        manifest: SkillManifest,
        request: SkillRunRequest,
        memories: list,
    ) -> str:
        template_text = "User intent: $user_intent\nMemory cards:\n$memory_cards\n"
        if manifest.entry.prompt_path:
            prompt_path = self.skills_dir / manifest.name / manifest.entry.prompt_path
            if prompt_path.exists():
                template_text = prompt_path.read_text(encoding="utf-8")
        memory_cards = self.privacy.render_memory_lines(
            memories,
            manifest.memory_scope.allowed_fields,
        )
        return Template(template_text).safe_substitute(
            user_intent=request.user_intent,
            memory_cards=memory_cards or "(no matching memory cards)",
            arguments=json.dumps(request.arguments, ensure_ascii=False),
        )
