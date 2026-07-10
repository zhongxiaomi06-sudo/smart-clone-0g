from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def backup_database(store, backup_dir: Path) -> Path:
    """使用 SQLite backup API 将数据库文件复制到备份目录。

    Args:
        store: SQLiteStore 实例,提供 database_path 属性。
        backup_dir: 备份目录路径,不存在时会自动创建。

    Returns:
        备份文件路径。

    Raises:
        RuntimeError: 当备份过程发生异常时,记录日志后重新抛出。
    """
    # 确保备份目录存在
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 生成带时间戳的备份文件名
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"smart_avatar_backup_{timestamp}.db"

    logger.info("开始备份数据库到 %s", backup_path)
    source_connection = None
    target_connection = None
    try:
        # 使用 SQLite 的 backup API 在线复制数据库
        source_connection = sqlite3.connect(str(store.database_path))
        target_connection = sqlite3.connect(str(backup_path))
        source_connection.backup(target_connection)
        logger.info("数据库备份完成: %s", backup_path)
        return backup_path
    except Exception as exc:
        # 备份失败时记录日志并抛出
        logger.error("数据库备份失败: %s", exc, exc_info=True)
        # 清理可能生成的不完整备份文件
        if backup_path.exists():
            try:
                backup_path.unlink()
            except OSError:
                pass
        raise RuntimeError(f"数据库备份失败: {exc}") from exc
    finally:
        # 确保连接被关闭
        if target_connection is not None:
            target_connection.close()
        if source_connection is not None:
            source_connection.close()


def export_to_json(store, output_path: Path) -> Path:
    """将 store 中的各类数据导出为 JSON 文件。

    导出内容包括:memories、states、recordings、audit_events、credentials,
    每类数据限制 10000 条。recordings 排除 storage_path 字段以避免泄露本地路径。

    Args:
        store: SQLiteStore 实例。
        output_path: 输出 JSON 文件路径。

    Returns:
        输出文件路径。
    """
    logger.info("开始导出数据到 JSON: %s", output_path)

    # 每类数据限制 10000 条
    export_limit = 10000

    # 加载各类数据
    memories = store.list_memories(limit=export_limit)
    states = store.list_states(limit=export_limit)
    recordings = store.list_recordings(limit=export_limit)
    audit_events = store.list_audit_events(limit=export_limit)
    credentials = store.list_credentials(limit=export_limit)

    logger.info(
        "数据加载完成: memories=%d, states=%d, recordings=%d, audit_events=%d, credentials=%d",
        len(memories),
        len(states),
        len(recordings),
        len(audit_events),
        len(credentials),
    )

    # 转为可序列化字典;recordings 排除 storage_path 字段
    payload = {
        "memories": [card.model_dump() for card in memories],
        "states": [card.model_dump() for card in states],
        "recordings": [
            recording.model_dump(exclude={"storage_path"}) for recording in recordings
        ],
        "audit_events": [event.model_dump() for event in audit_events],
        "credentials": [record.model_dump() for record in credentials],
    }

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入 JSON 文件
    with output_path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)

    logger.info("JSON 导出完成: %s", output_path)
    return output_path


def backup_all(store, backup_dir: Path) -> dict:
    """同时执行数据库文件备份和 JSON 导出。

    Args:
        store: SQLiteStore 实例。
        backup_dir: 备份目录路径。

    Returns:
        包含 "db_backup" 和 "json_export" 两个键的字典,值分别为对应文件路径。
    """
    logger.info("开始执行完整备份(数据库 + JSON)")

    # 执行数据库文件备份
    db_backup_path = backup_database(store, backup_dir)

    # JSON 导出文件名与数据库备份保持一致的时间戳风格
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = backup_dir / f"smart_avatar_export_{timestamp}.json"
    json_export_path = export_to_json(store, json_path)

    logger.info("完整备份完成")
    return {"db_backup": db_backup_path, "json_export": json_export_path}
