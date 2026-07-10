from __future__ import annotations

import datetime
import json
import logging
import sys


# logging.LogRecord 内置属性集合,用于区分 extra 自定义字段
_RESERVED_LOGRECORD_ATTRS = frozenset(
    {
        "name", "msg", "args", "created", "relativeCreated", "exc_info",
        "exc_text", "stack_info", "lineno", "funcName", "levelno",
        "levelname", "pathname", "filename", "module", "thread",
        "threadName", "processName", "process", "msecs", "message",
        "request_id", "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    """将 LogRecord 格式化为单行 JSON 字符串。"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.datetime.fromtimestamp(
                record.created, tz=datetime.timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        # request_id 由 LoggerAdapter 注入到 record 的 extra 中
        request_id = getattr(record, "request_id", None)
        if request_id is not None:
            payload["request_id"] = request_id
        # 合并额外的 extra 字段(排除 logging 内置属性)
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOGRECORD_ATTRS and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    """配置结构化 JSON 日志。

    为根 logger 添加输出到 stdout 的 StreamHandler,并设置根 logger 与
    "smart_avatar" logger 的级别。重复调用不会重复添加 handler。
    """
    root_logger = logging.getLogger()
    # 已存在 JsonFormatter 的 handler 则跳过,避免重复添加
    for handler in root_logger.handlers:
        if isinstance(handler.formatter, JsonFormatter):
            return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    logging.getLogger("smart_avatar").setLevel(level)


def get_request_logger(request_id: str | None = None) -> logging.LoggerAdapter:
    """返回附带 request_id 的 LoggerAdapter,用于请求级日志追踪。"""
    logger = logging.getLogger("smart_avatar")
    extra = {"request_id": request_id} if request_id else {}
    return logging.LoggerAdapter(logger, extra)
