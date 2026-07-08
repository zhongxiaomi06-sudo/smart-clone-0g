from __future__ import annotations

import hashlib
import json
from typing import Any

from .audit import AuditService
from .domain import CredentialCreateRequest, CredentialRecord
from .storage import SQLiteStore


class CredentialService:
    def __init__(self, store: SQLiteStore, audit: AuditService) -> None:
        self.store = store
        self.audit = audit

    def create_hash_credential(self, request: CredentialCreateRequest) -> CredentialRecord:
        digest = self._digest(request.payload)
        record = CredentialRecord(
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            digest=digest,
            metadata=request.metadata,
        )
        saved = self.store.add_credential(record)
        self.audit.record(
            "credential.hash",
            f"{saved.subject_type}:{saved.subject_id}",
            {
                "credential_id": saved.id,
                "hash_algorithm": saved.hash_algorithm,
                "anchor_status": saved.anchor_status,
            },
        )
        return saved

    def _digest(self, payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

