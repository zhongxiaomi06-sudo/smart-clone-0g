from __future__ import annotations

import sqlite3

# 当前 schema 版本号
SCHEMA_VERSION = 2

# 需要添加 user_id 列的业务表
_BUSINESS_TABLES = (
    "memory_cards",
    "state_cards",
    "permission_grants",
    "audit_events",
    "credential_records",
    "audio_recordings",
    "memory_vectors",
)


def column_exists(connection: sqlite3.Connection, table: str, column: str) -> bool:
    """通过 PRAGMA table_info 检查指定表的列是否存在。"""
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    # PRAGMA table_info 返回列: (cid, name, type, notnull, dflt_value, pk)
    return any(row[1] == column for row in rows)


def migration_to_v2(connection: sqlite3.Connection) -> None:
    """迁移到 v2:为所有业务表添加 user_id 列并建立索引。"""
    for table in _BUSINESS_TABLES:
        # SQLite 的 ALTER TABLE ADD COLUMN 在列已存在时会报错,需先检查
        if not column_exists(connection, table, "user_id"):
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN user_id TEXT DEFAULT 'default'"
            )
        # 创建 user_id 列索引
        connection.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table}_user_id ON {table} (user_id)"
        )


def run_migrations(connection: sqlite3.Connection) -> int:
    """运行数据库迁移,返回迁移后的 schema 版本号。"""
    # 创建 schema_meta 元信息表
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )

    # 读取当前版本号,默认为 1
    row = connection.execute(
        "SELECT value FROM schema_meta WHERE key = 'version'"
    ).fetchone()
    current_version = int(row[0]) if row else 1

    # 版本低于 2 时执行 v2 迁移:为业务表添加 user_id 列
    if current_version < 2:
        migration_to_v2(connection)

    # 添加 users 用户表
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
        """
    )

    # 更新版本号
    connection.execute(
        "INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('version', ?)",
        (str(SCHEMA_VERSION),),
    )

    return SCHEMA_VERSION
