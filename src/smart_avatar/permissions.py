from __future__ import annotations

from .domain import PermissionGrant, utc_now
from .storage import SQLiteStore


class PermissionService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def grant(
        self,
        target: str,
        scope: list[str],
        expires_at: str | None = None,
        user_id: str = "default",
    ) -> PermissionGrant:
        return self.store.add_permission(
            PermissionGrant(target=target, scope=scope, expires_at=expires_at),
            user_id=user_id,
        )

    def revoke(self, grant_id: str) -> PermissionGrant | None:
        return self.store.revoke_permission(grant_id, utc_now())

    def has_scope(self, token: str | None, required_scopes: list[str]) -> bool:
        if not required_scopes:
            return True
        if token is None:
            return False
        grant = self.store.get_permission(token)
        if grant is None or grant.revoked_at is not None:
            return False
        return set(required_scopes).issubset(set(grant.scope))
