# ===== 阶段 1: builder =====
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir --prefix=/install .

# ===== 阶段 2: runtime =====
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV SMART_AVATAR_CONFIG=/app/config/app.json

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# 从 builder 阶段复制已安装的包
COPY --from=builder /install /usr/local
COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY skills ./skills
COPY tools ./tools
COPY web ./web

# 创建数据目录并设置权限
RUN mkdir -p /app/data /app/data/recordings /app/data/backups && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"

CMD ["python", "-m", "uvicorn", "smart_avatar.app:app", "--host", "0.0.0.0", "--port", "8000"]
