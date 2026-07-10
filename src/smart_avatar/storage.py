from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .domain import (
    AuditEvent,
    AudioRecording,
    CredentialRecord,
    MemoryCard,
    MemoryQuery,
    PermissionGrant,
    StateCard,
)
from .embeddings import cosine_similarity


class SQLiteStore:
    def __init__(self, database_path: Path, embedding_client=None) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedding_client = embedding_client
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                create table if not exists memory_cards (
                    id text primary key,
                    payload text not null,
                    created_at text not null
                );
                create table if not exists state_cards (
                    id text primary key,
                    payload text not null,
                    created_at text not null
                );
                create table if not exists permission_grants (
                    id text primary key,
                    target text not null,
                    payload text not null,
                    created_at text not null,
                    revoked_at text
                );
                create table if not exists audit_events (
                    id text primary key,
                    event_type text not null,
                    target text not null,
                    payload text not null,
                    created_at text not null
                );
                create table if not exists credential_records (
                    id text primary key,
                    subject_type text not null,
                    subject_id text not null,
                    payload text not null,
                    created_at text not null
                );
                create table if not exists audio_recordings (
                    id text primary key,
                    payload text not null,
                    created_at text not null
                );
                create table if not exists memory_vectors (
                    memory_id text primary key,
                    vector text not null,
                    created_at text not null
                );
                """
            )

    def add_memory(self, card: MemoryCard) -> MemoryCard:
        payload = card.model_dump_json()
        with self._connect() as connection:
            connection.execute(
                "insert or replace into memory_cards (id, payload, created_at) values (?, ?, ?)",
                (card.id, payload, card.created_at),
            )
        # 同步更新向量索引(设计 5.2:事件和洞察字段转为向量)
        if self.embedding_client:
            text = self._memory_text(card)
            vector = self.embedding_client.embed(text)
            with self._connect() as connection:
                connection.execute(
                    "insert or replace into memory_vectors (memory_id, vector, created_at) values (?, ?, ?)",
                    (card.id, json.dumps(vector), card.created_at),
                )
        return card

    def get_memory(self, memory_id: str) -> MemoryCard | None:
        with self._connect() as connection:
            row = connection.execute(
                "select payload from memory_cards where id = ?",
                (memory_id,),
            ).fetchone()
        if row is None:
            return None
        return MemoryCard.model_validate_json(row["payload"])

    def delete_memory(self, memory_id: str) -> MemoryCard | None:
        with self._connect() as connection:
            row = connection.execute(
                "select payload from memory_cards where id = ?",
                (memory_id,),
            ).fetchone()
            if row is None:
                return None
            connection.execute("delete from memory_cards where id = ?", (memory_id,))
            connection.execute("delete from memory_vectors where memory_id = ?", (memory_id,))
        return MemoryCard.model_validate_json(row["payload"])

    def list_memories(self, limit: int = 50) -> list[MemoryCard]:
        with self._connect() as connection:
            rows = connection.execute(
                "select payload from memory_cards order by created_at desc limit ?",
                (limit,),
            ).fetchall()
        return [MemoryCard.model_validate_json(row["payload"]) for row in rows]

    @staticmethod
    def _memory_text(card: MemoryCard) -> str:
        parts = [card.event_summary]
        if card.insight:
            parts.append(card.insight)
        if card.emotion:
            parts.append(card.emotion.label)
        parts.extend(card.personality_signals)
        parts.extend(card.tags)
        return " ".join(parts)

    def query_memories(self, query: MemoryQuery) -> list[MemoryCard]:
        cards = self.list_memories(limit=500)
        if query.tags:
            cards = [card for card in cards if set(query.tags).intersection(card.tags)]
        if query.time_range:
            cards = [card for card in cards if card.time_range == query.time_range]

        query_text = query.query.strip()
        if not query_text:
            return cards[: query.limit]

        # 向量语义检索(设计 5.2:支持语义相似度检索)
        if self.embedding_client:
            return self._vector_search(query_text, cards, query.limit)

        # 关键词检索兜底(无嵌入器时使用)
        terms = [term.lower() for term in query_text.split() if term.strip()]
        if terms:
            matched = [card for card in cards if self._matches_terms(card, terms)]
            if not matched:
                matched = self._loose_match(query_text, cards)
            cards = matched
        return cards[: query.limit]

    def _vector_search(
        self,
        query_text: str,
        cards: list[MemoryCard],
        limit: int,
    ) -> list[MemoryCard]:
        """向量语义检索。对查询文本编码,与所有记忆卡片向量计算余弦相似度排序。"""
        query_vec = self.embedding_client.embed(query_text)
        # 从数据库加载已存向量
        vector_map: dict[str, list[float]] = {}
        with self._connect() as connection:
            rows = connection.execute(
                "select memory_id, vector from memory_vectors"
            ).fetchall()
        for row in rows:
            vector_map[row["memory_id"]] = json.loads(row["vector"])

        scored: list[tuple[float, MemoryCard]] = []
        for card in cards:
            vec = vector_map.get(card.id)
            if vec is None:
                # 向量缺失时实时生成
                vec = self.embedding_client.embed(self._memory_text(card))
            score = cosine_similarity(query_vec, vec)
            scored.append((score, card))

        scored.sort(key=lambda item: item[0], reverse=True)
        # 过滤掉相似度过低的结果
        threshold = 0.01
        return [card for score, card in scored[:limit] if score >= threshold]

    def _matches_terms(self, card: MemoryCard, terms: list[str]) -> bool:
        values: list[str] = [
            card.event_summary,
            card.insight or "",
            " ".join(card.personality_signals),
            " ".join(card.tags),
        ]
        haystack = " ".join(values).lower()
        return any(term in haystack for term in terms)

    def _loose_match(self, query: str, cards: list[MemoryCard]) -> list[MemoryCard]:
        query_chars = {char for char in query.lower() if not char.isspace()}
        scored: list[tuple[int, MemoryCard]] = []
        for card in cards:
            values = [
                card.event_summary,
                card.insight or "",
                " ".join(card.personality_signals),
                " ".join(card.tags),
            ]
            haystack_chars = set(" ".join(values).lower())
            score = len(query_chars.intersection(haystack_chars))
            if score >= 2:
                scored.append((score, card))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [card for _, card in scored]

    def add_state(self, card: StateCard) -> StateCard:
        with self._connect() as connection:
            connection.execute(
                "insert or replace into state_cards (id, payload, created_at) values (?, ?, ?)",
                (card.id, card.model_dump_json(), card.created_at),
            )
        return card

    def list_states(self, limit: int = 50) -> list[StateCard]:
        with self._connect() as connection:
            rows = connection.execute(
                "select payload from state_cards order by created_at desc limit ?",
                (limit,),
            ).fetchall()
        return [StateCard.model_validate_json(row["payload"]) for row in rows]

    def query_states(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
    ) -> list[StateCard]:
        cards = self.list_states(limit=500)
        if date_from:
            cards = [card for card in cards if card.date >= date_from]
        if date_to:
            cards = [card for card in cards if card.date <= date_to]
        return cards[:limit]

    def add_permission(self, grant: PermissionGrant) -> PermissionGrant:
        with self._connect() as connection:
            connection.execute(
                """
                insert or replace into permission_grants
                (id, target, payload, created_at, revoked_at)
                values (?, ?, ?, ?, ?)
                """,
                (
                    grant.id,
                    grant.target,
                    grant.model_dump_json(),
                    grant.created_at,
                    grant.revoked_at,
                ),
            )
        return grant

    def get_permission(self, grant_id: str) -> PermissionGrant | None:
        with self._connect() as connection:
            row = connection.execute(
                "select payload from permission_grants where id = ?",
                (grant_id,),
            ).fetchone()
        if row is None:
            return None
        return PermissionGrant.model_validate_json(row["payload"])

    def list_permissions(self, target: str | None = None) -> list[PermissionGrant]:
        sql = "select payload from permission_grants"
        params: tuple[Any, ...] = ()
        if target:
            sql += " where target = ?"
            params = (target,)
        sql += " order by created_at desc"
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [PermissionGrant.model_validate_json(row["payload"]) for row in rows]

    def revoke_permission(self, grant_id: str, revoked_at: str) -> PermissionGrant | None:
        grant = self.get_permission(grant_id)
        if grant is None:
            return None
        grant.revoked_at = revoked_at
        return self.add_permission(grant)

    def add_audit_event(self, event: AuditEvent) -> AuditEvent:
        with self._connect() as connection:
            connection.execute(
                """
                insert into audit_events (id, event_type, target, payload, created_at)
                values (?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.event_type,
                    event.target,
                    json.dumps(event.payload, ensure_ascii=False),
                    event.created_at,
                ),
            )
        return event

    def list_audit_events(self, limit: int = 100) -> list[AuditEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select id, event_type, target, payload, created_at
                from audit_events
                order by created_at desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        return [
            AuditEvent(
                id=row["id"],
                event_type=row["event_type"],
                target=row["target"],
                payload=json.loads(row["payload"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def add_credential(self, record: CredentialRecord) -> CredentialRecord:
        with self._connect() as connection:
            connection.execute(
                """
                insert into credential_records (id, subject_type, subject_id, payload, created_at)
                values (?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.subject_type,
                    record.subject_id,
                    record.model_dump_json(),
                    record.created_at,
                ),
            )
        return record

    def list_credentials(
        self,
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        limit: int = 100,
    ) -> list[CredentialRecord]:
        sql = "select payload from credential_records"
        params: list[Any] = []
        clauses: list[str] = []
        if subject_type:
            clauses.append("subject_type = ?")
            params.append(subject_type)
        if subject_id:
            clauses.append("subject_id = ?")
            params.append(subject_id)
        if clauses:
            sql += " where " + " and ".join(clauses)
        sql += " order by created_at desc limit ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [CredentialRecord.model_validate_json(row["payload"]) for row in rows]

    def add_recording(self, recording: AudioRecording) -> AudioRecording:
        with self._connect() as connection:
            connection.execute(
                "insert or replace into audio_recordings (id, payload, created_at) values (?, ?, ?)",
                (recording.id, recording.model_dump_json(), recording.created_at),
            )
        return recording

    def get_recording(self, recording_id: str) -> AudioRecording | None:
        with self._connect() as connection:
            row = connection.execute(
                "select payload from audio_recordings where id = ?",
                (recording_id,),
            ).fetchone()
        if row is None:
            return None
        return AudioRecording.model_validate_json(row["payload"])

    def list_recordings(self, limit: int = 100) -> list[AudioRecording]:
        with self._connect() as connection:
            rows = connection.execute(
                "select payload from audio_recordings order by created_at desc limit ?",
                (limit,),
            ).fetchall()
        return [AudioRecording.model_validate_json(row["payload"]) for row in rows]

    def delete_recording(self, recording_id: str) -> AudioRecording | None:
        with self._connect() as connection:
            row = connection.execute(
                "select payload from audio_recordings where id = ?",
                (recording_id,),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "delete from audio_recordings where id = ?",
                (recording_id,),
            )
        return AudioRecording.model_validate_json(row["payload"])
