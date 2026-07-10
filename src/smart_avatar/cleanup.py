from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from .audit import AuditService
from .storage import SQLiteStore

logger = logging.getLogger(__name__)


def _parse_iso_datetime(dt_str: str) -> datetime:
    """解析 ISO 格式时间字符串,返回 UTC 时区感知的 datetime。

    兼容以 Z 结尾的 UTC 写法;若字符串不带时区信息,则按 UTC 处理。
    """
    # 兼容 ISO 8601 中以 Z 表示 UTC 的写法
    normalized = dt_str
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    dt = datetime.fromisoformat(normalized)
    # naive datetime 视为 UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _age_days(created_at: str) -> float:
    """计算从 created_at 到当前 UTC 时间的天数。"""
    created = _parse_iso_datetime(created_at)
    now = datetime.now(timezone.utc)
    return (now - created).total_seconds() / 86400


def cleanup_expired_recordings(
    store: SQLiteStore,
    recordings_dir: Path,
    audit: AuditService,
) -> dict:
    """清理已过期的录音文件及其数据库记录。

    遍历所有录音,对设置了 auto_delete_after_days 且已超过保留天数的录音:
      a. 删除磁盘上的录音文件(如果存在)
      b. 从数据库删除录音记录
      c. 记录审计日志

    文件删除失败不会中断整体清理过程,错误会被收集到返回结果中。

    返回: {"checked": 检查数量, "deleted": 删除数量, "errors": 错误列表}
    """
    checked = 0
    deleted = 0
    errors: list[str] = []

    recordings = store.list_recordings(limit=100000)
    logger.info("开始清理过期录音,共 %d 条记录待检查", len(recordings))

    for recording in recordings:
        checked += 1

        # 未设置自动删除天数,跳过
        if recording.auto_delete_after_days is None:
            continue

        # 解析创建时间,计算已存在天数
        try:
            age = _age_days(recording.created_at)
        except Exception as exc:
            error_msg = f"录音 {recording.id} 创建时间解析失败: {exc}"
            logger.warning(error_msg)
            errors.append(error_msg)
            continue

        # 未超过保留天数,跳过
        if age < recording.auto_delete_after_days:
            continue

        logger.info(
            "录音 %s 已过期(已存在 %.2f 天, 保留期 %d 天),开始清理",
            recording.id,
            age,
            recording.auto_delete_after_days,
        )

        # a. 删除磁盘上的录音文件(如果存在)
        file_path = Path(recording.storage_path)
        if not file_path.is_absolute():
            file_path = recordings_dir / file_path

        if file_path.is_file():
            try:
                file_path.unlink()
                logger.info("已删除录音文件: %s", file_path)
            except OSError as exc:
                # 文件删除失败不中断清理过程,记录错误后继续
                error_msg = f"删除录音文件失败 {file_path}: {exc}"
                logger.warning(error_msg)
                errors.append(error_msg)

        # b. 从数据库删除录音记录
        try:
            store.delete_recording(recording.id)
            deleted += 1
            logger.info("已从数据库删除录音记录: %s", recording.id)
        except Exception as exc:
            error_msg = f"删除录音数据库记录失败 {recording.id}: {exc}"
            logger.warning(error_msg)
            errors.append(error_msg)
            # 数据库记录删除失败则不再记录审计日志
            continue

        # c. 记录审计日志
        try:
            audit.record(
                "recording.auto_delete",
                recording.id,
                {
                    "file_name": recording.file_name,
                    "age_days": round(age, 2),
                },
            )
        except Exception as exc:
            error_msg = f"记录审计日志失败 {recording.id}: {exc}"
            logger.warning(error_msg)
            errors.append(error_msg)

    result = {"checked": checked, "deleted": deleted, "errors": errors}
    logger.info(
        "清理完成: 检查 %d 条, 删除 %d 条, 错误 %d 条",
        checked,
        deleted,
        len(errors),
    )
    return result
