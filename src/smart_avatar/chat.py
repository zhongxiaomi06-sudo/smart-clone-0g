from __future__ import annotations

from .audit import AuditService
from .domain import ChatRequest, ChatResponse, Citation, MemoryQuery, SkillRunRequest
from .skills import SkillRegistry
from .storage import SQLiteStore


class ChatOrchestrator:
    def __init__(self, *, store: SQLiteStore, skills: SkillRegistry, audit: AuditService) -> None:
        self.store = store
        self.skills = skills
        self.audit = audit

    def handle(self, request: ChatRequest) -> ChatResponse:
        skill = (
            self.skills.get(request.skill_name)
            if request.skill_name
            else self.skills.match(request.message)
        )
        if skill is not None:
            result = self.skills.run(
                skill.name,
                SkillRunRequest(
                    user_intent=request.message,
                    permission_token=request.permission_token,
                    user_confirmed=request.user_confirmed,
                    memory_query=MemoryQuery(query=request.message, limit=request.limit),
                ),
            )
            if result.status == "permission_required":
                return ChatResponse(
                    action="permission_required",
                    answer="这个 Skill 需要你确认授权后才能读取相关记忆。",
                    citations=result.used_context,
                    skill_result=result,
                )
            return ChatResponse(
                action="skill_run",
                answer=f"已调用 Skill：{skill.display_name}",
                citations=result.used_context,
                skill_result=result,
            )

        query = MemoryQuery(query=request.message, limit=request.limit)
        memories = self.store.query_memories(query)
        citations = [
            Citation(source_type="memory", source_id=card.id, summary=card.event_summary)
            for card in memories
        ]
        self.audit.record(
            "chat.memory_query",
            "chat",
            {"query": request.message, "memory_ids": [card.id for card in memories]},
        )
        if not memories:
            return ChatResponse(
                action="memory_answer",
                answer="我还没有找到足够相关的记忆。你可以补充更多片段，或指定一个 Skill 来处理。",
                citations=[],
            )
        summaries = "\n".join(f"- {card.event_summary}" for card in memories)
        return ChatResponse(
            action="memory_answer",
            answer=f"我找到了这些相关记忆线索：\n{summaries}",
            citations=citations,
        )
