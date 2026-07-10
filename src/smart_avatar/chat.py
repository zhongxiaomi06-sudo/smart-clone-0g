from __future__ import annotations

import json
import re

from .audit import AuditService
from .domain import ChatRequest, ChatResponse, Citation, MemoryQuery, SkillRunRequest
from .models import ModelClient
from .skills import SkillRegistry
from .storage import SQLiteStore


# 意图关键词(设计 11.3 路由规则)
_INTENT_PATTERNS = {
    "story": [
        "故事", "写一篇", "创作", "神话", "叙事", "改写", "续写",
        "小说", "文学", "今天的故事", "每日故事",
    ],
    "review": [
        "复盘", "总结", "回顾这周", "一周", "本周", "周报",
        "模式", "趋势", "报告", "觉察", "情绪图谱",
    ],
    "plan": [
        "计划", "安排", "日程", "建议", "明天做什么", "待办",
        "日程建议",
    ],
    "relationship": [
        "关系", "沟通模式", "朋友", "同事", "互动",
    ],
}

_RECALL_SYSTEM_PROMPT = """你是用户的回忆整理助手。你只能基于提供的脱敏记忆卡片进行回答。

回答要求:
1. 先说明你引用了哪些记忆线索。
2. 区分"记忆事实""合理推断""建议"。
3. 如果证据不足,直接说明不足,不要强行下结论。
4. 语气温和、具体、克制。
5. 不提供医疗、法律、财务等高风险结论。

请按以下结构组织回答:
【记忆线索】列出引用的记忆卡片摘要。
【回答】基于线索的回答内容,必要时标注[推断]或[建议]。
【证据不足】如果有的话,说明哪些方面证据不够。"""

_ROUTER_SYSTEM_PROMPT = """你是智慧分身的对话路由器。根据用户输入判断意图。

路由规则:
1. 如果用户询问过往经历,优先检索记忆并直接回答。
2. 如果用户要求总结、复盘、创作、计划或状态分析,选择最匹配的 Skill。
3. 如果意图不明确,返回 clarify。

输出 JSON:{"action": "memory_answer|skill_run|clarify", "skill_name": "Skill名称或null", "reason": "判断原因"}"""


class ChatOrchestrator:
    def __init__(
        self,
        *,
        store: SQLiteStore,
        skills: SkillRegistry,
        audit: AuditService,
        model_client: ModelClient | None = None,
    ) -> None:
        self.store = store
        self.skills = skills
        self.audit = audit
        self.model_client = model_client

    def handle(self, request: ChatRequest) -> ChatResponse:
        # 1. 如果用户手动指定了 Skill,直接路由到该 Skill
        if request.skill_name:
            return self._route_to_skill(request.skill_name, request)

        # 2. 意图判断:先尝试触发词匹配,再尝试模型路由
        intent = self._classify_intent(request.message)

        # 3. 如果意图匹配到某个 Skill 类型,尝试路由
        skill = self._match_skill_by_intent(intent, request.message)
        if skill is not None:
            return self._route_to_skill(skill.name, request)

        # 4. 默认走记忆检索回答
        return self._memory_answer(request)

    def _classify_intent(self, message: str) -> str:
        """意图分类。设计 11.3:判断回忆/创作/复盘/计划/关系。"""
        normalized = message.lower().strip()

        # 关键词匹配
        for intent, keywords in _INTENT_PATTERNS.items():
            if any(kw in normalized for kw in keywords):
                return intent

        # 模型路由(dry-run 时跳过)
        if self.model_client and not self._is_dry_run():
            try:
                raw = self.model_client.generate(
                    system_prompt=_ROUTER_SYSTEM_PROMPT,
                    user_prompt=f"用户输入:{message}\n可用 Skill:{', '.join(s.name for s in self.skills.list())}",
                )
                parsed = self._parse_json(raw)
                if parsed and parsed.get("action") == "skill_run" and parsed.get("skill_name"):
                    return parsed["skill_name"]
            except Exception:  # noqa: BLE001
                # 模型路由失败:降级到关键词匹配结果(已是 recall)
                pass

        return "recall"

    def _match_skill_by_intent(self, intent: str, message: str) -> any:
        """根据意图匹配已注册的 Skill。"""
        # 先用 Skill 自身的触发词匹配
        matched = self.skills.match(message)
        if matched is not None:
            return matched

        # 按意图类型匹配 Skill 名称
        intent_skill_map = {
            "story": ["daily_story", "story"],
            "review": ["weekly_review", "self_awareness", "review"],
            "plan": ["daily_plan", "schedule"],
            "relationship": ["relationship_insight", "relationship"],
        }
        target_names = intent_skill_map.get(intent, [])
        for skill_manifest in self.skills.list():
            if skill_manifest.name in target_names:
                return skill_manifest
        return None

    def _route_to_skill(self, skill_name: str, request: ChatRequest) -> ChatResponse:
        result = self.skills.run(
            skill_name,
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
                answer="这个 Skill 需要你确认授权后才能读取相关记忆。请勾选「本次确认授权」后重试。",
                citations=result.used_context,
                skill_result=result,
            )
        if result.status == "not_found":
            return ChatResponse(
                action="clarify",
                answer=f"未找到 Skill:{skill_name}。请检查 Skill 是否已注册。",
                citations=[],
            )
        return ChatResponse(
            action="skill_run",
            answer=result.result.get("model_output", f"已调用 Skill:{skill_name}"),
            citations=result.used_context,
            skill_result=result,
        )

    def _memory_answer(self, request: ChatRequest) -> ChatResponse:
        """记忆检索回答。设计 11.2:基于记忆回答,区分事实与推断。"""
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
                answer="我还没有找到足够相关的记忆。你可以补充更多片段,或指定一个 Skill 来处理(如在消息中提到「故事」「复盘」等关键词)。",
                citations=[],
            )

        # 如果有真实模型,用模型组织回答
        if self.model_client and not self._is_dry_run():
            memory_context = self._format_memory_context(memories)
            try:
                answer = self.model_client.generate(
                    system_prompt=_RECALL_SYSTEM_PROMPT,
                    user_prompt=f"用户问题:{request.message}\n\n可用记忆卡片:\n{memory_context}",
                )
            except Exception as exc:  # noqa: BLE001
                # 模型调用失败:返回明确的错误,不降级到 dry-run 占位文本
                self.audit.record(
                    "chat.model_error",
                    "chat",
                    {"query": request.message, "error": str(exc)},
                )
                return ChatResponse(
                    action="memory_answer",
                    answer=(
                        f"已检索到 {len(memories)} 条相关记忆,但模型调用失败。\n"
                        f"错误信息:{exc}\n\n"
                        "请检查 API Key 配置或网络后重试。"
                    ),
                    citations=citations,
                )
        else:
            # dry-run 模式:结构化展示记忆线索
            answer = self._format_dry_run_answer(request.message, memories)

        return ChatResponse(
            action="memory_answer",
            answer=answer,
            citations=citations,
        )

    def _format_memory_context(self, memories: list) -> str:
        lines = []
        for i, card in enumerate(memories, 1):
            emotion = f", 情绪:{card.emotion.label}" if card.emotion else ""
            insight = f", 洞察:{card.insight}" if card.insight else ""
            lines.append(f"{i}. [{card.time_range or '未标注时间'}] {card.event_summary}{emotion}{insight}")
        return "\n".join(lines)

    def _format_dry_run_answer(self, question: str, memories: list) -> str:
        """dry-run 模式下的结构化回答,遵循设计 11.2 的回答结构。"""
        lines = ["【记忆线索】"]
        for i, card in enumerate(memories, 1):
            emotion = f"(情绪:{card.emotion.label})" if card.emotion else ""
            lines.append(f"{i}. [{card.time_range or '未标注'}] {card.event_summary} {emotion}")

        lines.append("")
        lines.append("【回答】")
        lines.append(f"基于以上 {len(memories)} 条记忆线索,以下是与「{question}」相关的整理:")
        lines.append("")
        for card in memories:
            if card.insight:
                lines.append(f"- {card.event_summary} → [推断] {card.insight}")

        lines.append("")
        lines.append("【说明】")
        lines.append("[记忆事实] 以上事件摘要均来自你已记录的脱敏记忆卡片。")
        lines.append("[推断] 标注的内容来自卡片中的洞察字段,属于合理推断而非事实复述。")
        lines.append("[证据不足] 当前为 dry-run 模式,未调用真实大模型进行深度分析。配置模型后可获得更精准的回答。")

        return "\n".join(lines)

    def _is_dry_run(self) -> bool:
        if self.model_client is None:
            return True
        return getattr(self.model_client, "model_name", "") in ("dry-run", "") or \
            hasattr(self.model_client, "config") and getattr(self.model_client.config, "provider", "") == "dry_run"

    @staticmethod
    def _parse_json(raw: str) -> dict | None:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
