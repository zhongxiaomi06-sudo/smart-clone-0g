from __future__ import annotations

from .domain import AuditEvent
from .storage import SQLiteStore


class AuditService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def record(
        self, event_type: str, target: str, payload: dict, user_id: str = "default"
    ) -> AuditEvent:
        return self.store.add_audit_event(
            AuditEvent(event_type=event_type, target=target, payload=payload),
            user_id=user_id,
        )

