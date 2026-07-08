from __future__ import annotations

import json
from pathlib import Path

from .audit import AuditService
from .domain import ToolCallRequest, ToolCallResult, ToolManifest
from .permissions import PermissionService


class ToolRegistry:
    def __init__(self, tools_dir: Path) -> None:
        self.tools_dir = tools_dir
        self.tools_dir.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[ToolManifest]:
        manifests: list[ToolManifest] = []
        for manifest_path in self.tools_dir.glob("*/tool.json"):
            manifests.append(self._load_manifest(manifest_path))
        return sorted(manifests, key=lambda manifest: manifest.name)

    def get(self, name: str) -> ToolManifest | None:
        manifest_path = self.tools_dir / name / "tool.json"
        if not manifest_path.exists():
            return None
        return self._load_manifest(manifest_path)

    def _load_manifest(self, manifest_path: Path) -> ToolManifest:
        with manifest_path.open("r", encoding="utf-8") as file:
            return ToolManifest.model_validate(json.load(file))


class McpGateway:
    def __init__(
        self,
        *,
        tools_dir: Path,
        audit: AuditService,
        permissions: PermissionService,
    ) -> None:
        self.registry = ToolRegistry(tools_dir)
        self.audit = audit
        self.permissions = permissions

    def call(self, request: ToolCallRequest) -> ToolCallResult:
        manifest = self.registry.get(request.tool_name)
        if manifest is None:
            audit = self.audit.record(
                "tool.not_configured",
                request.tool_name,
                {"arguments": request.arguments},
            )
            return ToolCallResult(
                tool_name=request.tool_name,
                status="not_configured",
                result={
                    "message": "No MCP adapter is configured for this tool yet.",
                    "next_step": "Register a tool manifest before enabling external calls.",
                },
                audit_id=audit.id,
            )

        if not manifest.enabled:
            audit = self.audit.record(
                "tool.disabled",
                manifest.name,
                {"arguments": request.arguments},
            )
            return ToolCallResult(
                tool_name=manifest.name,
                status="not_configured",
                result={"message": "This tool is registered but disabled."},
                audit_id=audit.id,
            )

        if not self.permissions.has_scope(request.permission_token, manifest.permissions):
            audit = self.audit.record(
                "tool.permission_required",
                manifest.name,
                {"permissions": manifest.permissions},
            )
            return ToolCallResult(
                tool_name=manifest.name,
                status="permission_required",
                result={"missing_permissions": manifest.permissions},
                audit_id=audit.id,
            )

        if manifest.entry.kind == "dry_run":
            audit = self.audit.record(
                "tool.dry_run",
                manifest.name,
                {"arguments": request.arguments},
            )
            return ToolCallResult(
                tool_name=manifest.name,
                status="completed",
                result={
                    "message": "Dry-run tool adapter completed.",
                    "arguments": request.arguments,
                    "tool": manifest.model_dump(),
                },
                audit_id=audit.id,
            )

        audit = self.audit.record(
            "tool.not_implemented",
            request.tool_name,
            {"arguments": request.arguments},
        )
        return ToolCallResult(
            tool_name=request.tool_name,
            status="error",
            result={
                "message": "Tool manifest exists, but its adapter kind is not implemented.",
                "adapter_kind": manifest.entry.kind,
            },
            audit_id=audit.id,
        )
