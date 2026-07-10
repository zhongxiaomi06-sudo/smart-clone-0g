from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

import numpy as np

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
        # 线程本地连接池,每个线程复用自己的连接
        self._local = threading.local()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        # 复用线程本地连接池中的连接
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            return connection
        # 创建新连接并配置
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        # 启用 WAL 模式提升并发读写性能
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA foreign_keys=ON")
        self._local.connection = connection
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                create table if not exists memory_cards (
                    id text primary key,
                    payload text not null,
                    created_at text not null,
                    user_id text not null default 'default'
                );
                create table if not exists state_cards (
                    id text primary key,
                    payload text not null,
                    created_at text not null,
                    user_id text not null default 'default'
                );
                create table if not exists permission_grants (
                    id text primary key,
                    target text not null,
                    payload text not null,
                    created_at text not null,
                    revoked_at text,
                    user_id text not null default 'default'
                );
                create table if not exists audit_events (
                    id text primary key,
                    event_type text not null,
                    target text not null,
                    payload text not null,
                    created_at text not null,
                    user_id text not null default 'default'
                );
                create table if not exists credential_records (
                    id text primary key,
                    subject_type text not null,
                    subject_id text not null,
                    payload text not null,
                    created_at text not null,
                    user_id text not null default 'default'
                );
                create table if not exists audio_recordings (
                    id text primary key,
                    payload text not null,
                    created_at text not null,
                    user_id text not null default 'default'
                );
                create table if not exists memory_vectors (
                    memory_id text primary key,
                    vector text not null,
                    created_at text not null
                );
                """
            )
            # 在 schema 创建之后执行数据库迁移
            from .migration import run_migrations

            run_migrations(connection)

    def add_memory(self, card: MemoryCard, user_id: str = "default") -> MemoryCard:
        payload = card.model_dump_json()
        with self._connect() as connection:
            connection.execute(
                "insert or replace into memory_cards (id, payload, created_at, user_id) values (?, ?, ?, ?)",
                (card.id, payload, card.created_at, user_id),
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

    def get_memory(self, memory_id: str, user_id: str | None = None) -> MemoryCard | None:
        with self._connect() as connection:
            if user_id is not None:
                row = connection.execute(
                    "select payload from memory_cards where id = ? and user_id = ?",
                    (memory_id, user_id),
                ).fetchone()
            else:
                row = connection.execute(
                    "select payload from memory_cards where id = ?",
                    (memory_id,),
                ).fetchone()
        if row is None:
            return None
        return MemoryCard.model_validate_json(row["payload"])

    def delete_memory(self, memory_id: str, user_id: str | None = None) -> MemoryCard | None:
        with self._connect() as connection:
            if user_id is not None:
                row = connection.execute(
                    "select payload from memory_cards where id = ? and user_id = ?",
                    (memory_id, user_id),
                ).fetchone()
            else:
                row = connection.execute(
                    "select payload from memory_cards where id = ?",
                    (memory_id,),
                ).fetchone()
            if row is None:
                return None
            connection.execute("delete from memory_cards where id = ?", (memory_id,))
            connection.execute("delete from memory_vectors where memory_id = ?", (memory_id,))
        return MemoryCard.model_validate_json(row["payload"])

    def list_memories(self, limit: int = 50, user_id: str = "default") -> list[MemoryCard]:
        with self._connect() as connection:
            rows = connection.execute(
                "select payload from memory_cards where user_id = ? order by created_at desc limit ?",
                (user_id, limit),
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

    def query_memories(self, query: MemoryQuery, user_id: str = "default") -> list[MemoryCard]:
        cards = self.list_memories(limit=500, user_id=user_id)
        if query.tags:
            cards = [card for card in cards if set(query.tags).intersection(card.tags)]
        if query.time_range:
            cards = [card for card in cards if card.time_range == query.time_range]

        query_text = query.query.strip()
        if not query_text:
            return cards[: query.limit]

        # 向量语义检索(设计 5.2:支持语义相似度检索)
        if self.embedding_client:
            return self._vector_search(query_text, cards, query.limit, user_id=user_id)

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
        user_id: str = "default",
    ) -> list[MemoryCard]:
        """向量语义检索。使用 numpy 矩阵运算批量计算余弦相似度排序。"""
        query_vec = np.array(self.embedding_client.embed(query_text), dtype=np.float32)
        # 从数据库批量加载已存向量
        vector_map: dict[str, list[float]] = {}
        with self._connect() as connection:
            rows = connection.execute(
                "select memory_id, vector from memory_vectors"
            ).fetchall()
        for row in rows:
            vector_map[row["memory_id"]] = json.loads(row["vector"])

        # 构建向量矩阵
        card_vectors: list[list[float]] = []
        valid_cards: list[MemoryCard] = []
        for card in cards:
            vec = vector_map.get(card.id)
            if vec is None:
                # 向量缺失时实时生成
                vec = self.embedding_client.embed(self._memory_text(card))
            card_vectors.append(vec)
            valid_cards.append(card)

        if not valid_cards:
            return []

        matrix = np.array(card_vectors, dtype=np.float32)
        # 计算余弦相似度(矩阵运算)
        # 归一化
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        matrix_norm = matrix / norms
        query_norm = query_vec / (np.linalg.norm(query_vec) or 1)
        # 点积 = 余弦相似度(已归一化)
        scores = matrix_norm @ query_norm

        # 排序
        scored = list(zip(scores.tolist(), valid_cards))
        scored.sort(key=lambda x: x[0], reverse=True)
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

    def add_state(self, card: StateCard, user_id: str = "default") -> StateCard:
        with self._connect() as connection:
            connection.execute(
                "insert or replace into state_cards (id, payload, created_at, user_id) values (?, ?, ?, ?)",
                (card.id, card.model_dump_json(), card.created_at, user_id),
            )
        return card

    def list_states(self, limit: int = 50, user_id: str = "default") -> list[StateCard]:
        with self._connect() as connection:
            rows = connection.execute(
                "select payload from state_cards where user_id = ? order by created_at desc limit ?",
                (user_id, limit),
            ).fetchall()
        return [StateCard.model_validate_json(row["payload"]) for row in rows]

    def query_states(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        user_id: str = "default",
    ) -> list[StateCard]:
        cards = self.list_states(limit=500, user_id=user_id)
        if date_from:
            cards = [card for card in cards if card.date >= date_from]
        if date_to:
            cards = [card for card in cards if card.date <= date_to]
        return cards[:limit]

    def add_permission(self, grant: PermissionGrant, user_id: str = "default") -> PermissionGrant:
        with self._connect() as connection:
            connection.execute(
                """
                insert or replace into permission_grants
                (id, target, payload, created_at, revoked_at, user_id)
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    grant.id,
                    grant.target,
                    grant.model_dump_json(),
                    grant.created_at,
                    grant.revoked_at,
                    user_id,
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

    def list_permissions(
        self, target: str | None = None, user_id: str = "default"
    ) -> list[PermissionGrant]:
        sql = "select payload from permission_grants where user_id = ?"
        params: list[Any] = [user_id]
        if target:
            sql += " and target = ?"
            params.append(target)
        sql += " order by created_at desc"
        with self._connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [PermissionGrant.model_validate_json(row["payload"]) for row in rows]

    def revoke_permission(self, grant_id: str, revoked_at: str) -> PermissionGrant | None:
        grant = self.get_permission(grant_id)
        if grant is None:
            return None
        grant.revoked_at = revoked_at
        return self.add_permission(grant)

    def add_audit_event(self, event: AuditEvent, user_id: str = "default") -> AuditEvent:
        with self._connect() as connection:
            connection.execute(
                """
                insert into audit_events (id, event_type, target, payload, created_at, user_id)
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.event_type,
                    event.target,
                    json.dumps(event.payload, ensure_ascii=False),
                    event.created_at,
                    user_id,
                ),
            )
        return event

    def list_audit_events(self, limit: int = 100, user_id: str = "default") -> list[AuditEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select id, event_type, target, payload, created_at
                from audit_events
                where user_id = ?
                order by created_at desc
                limit ?
                """,
                (user_id, limit),
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

    def add_credential(self, record: CredentialRecord, user_id: str = "default") -> CredentialRecord:
        with self._connect() as connection:
            connection.execute(
                """
                insert into credential_records (id, subject_type, subject_id, payload, created_at, user_id)
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.subject_type,
                    record.subject_id,
                    record.model_dump_json(),
                    record.created_at,
                    user_id,
                ),
            )
        return record

    def list_credentials(
        self,
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        limit: int = 100,
        user_id: str = "default",
    ) -> list[CredentialRecord]:
        sql = "select payload from credential_records where user_id = ?"
        params: list[Any] = [user_id]
        clauses: list[str] = []
        if subject_type:
            clauses.append("subject_type = ?")
            params.append(subject_type)
        if subject_id:
            clauses.append("subject_id = ?")
            params.append(subject_id)
        if clauses:
            sql += " and " + " and ".join(clauses)
        sql += " order by created_at desc limit ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [CredentialRecord.model_validate_json(row["payload"]) for row in rows]

    def add_recording(self, recording: AudioRecording, user_id: str = "default") -> AudioRecording:
        with self._connect() as connection:
            connection.execute(
                "insert or replace into audio_recordings (id, payload, created_at, user_id) values (?, ?, ?, ?)",
                (recording.id, recording.model_dump_json(), recording.created_at, user_id),
            )
        return recording

    def get_recording(self, recording_id: str, user_id: str | None = None) -> AudioRecording | None:
        with self._connect() as connection:
            if user_id is not None:
                row = connection.execute(
                    "select payload from audio_recordings where id = ? and user_id = ?",
                    (recording_id, user_id),
                ).fetchone()
            else:
                row = connection.execute(
                    "select payload from audio_recordings where id = ?",
                    (recording_id,),
                ).fetchone()
        if row is None:
            return None
        return AudioRecording.model_validate_json(row["payload"])

    def list_recordings(self, limit: int = 100, user_id: str = "default") -> list[AudioRecording]:
        with self._connect() as connection:
            rows = connection.execute(
                "select payload from audio_recordings where user_id = ? order by created_at desc limit ?",
                (user_id, limit),
            ).fetchall()
        return [AudioRecording.model_validate_json(row["payload"]) for row in rows]

    def delete_recording(self, recording_id: str, user_id: str | None = None) -> AudioRecording | None:
        with self._connect() as connection:
            if user_id is not None:
                row = connection.execute(
                    "select payload from audio_recordings where id = ? and user_id = ?",
                    (recording_id, user_id),
                ).fetchone()
            else:
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

    def clear_all_memories(self, user_id: str = "default") -> int:
        """批量删除指定用户的所有记忆卡片及其向量索引,返回删除数量。"""
        with self._connect() as connection:
            # 先获取数量
            count = connection.execute(
                "select count(*) from memory_cards where user_id = ?", (user_id,)
            ).fetchone()[0]
            # 先删 vectors 再删 cards(依赖 cards 的 id 子查询定位 vectors)
            connection.execute(
                """
                delete from memory_vectors
                where memory_id in (select id from memory_cards where user_id = ?)
                """,
                (user_id,),
            )
            connection.execute(
                "delete from memory_cards where user_id = ?", (user_id,)
            )
        return count
