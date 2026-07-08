from __future__ import annotations

from typing import Any

from .domain import MemoryCard


DEFAULT_MEMORY_FIELDS = [
    "event_summary",
    "emotion",
    "insight",
    "personality_signals",
    "tags",
]


class PrivacyProjector:
    def project_memory(
        self,
        card: MemoryCard,
        allowed_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        fields = allowed_fields or DEFAULT_MEMORY_FIELDS
        projected: dict[str, Any] = {"id": card.id}
        for field in fields:
            if not hasattr(card, field):
                continue
            value = getattr(card, field)
            if hasattr(value, "model_dump"):
                value = value.model_dump()
            projected[field] = value
        return projected

    def render_memory_lines(
        self,
        cards: list[MemoryCard],
        allowed_fields: list[str] | None = None,
    ) -> str:
        lines: list[str] = []
        for card in cards:
            projected = self.project_memory(card, allowed_fields)
            values = ", ".join(
                f"{key}={value}"
                for key, value in projected.items()
                if key != "id" and value not in (None, "", [], {})
            )
            lines.append(f"- {projected['id']}: {values}")
        return "\n".join(lines)
