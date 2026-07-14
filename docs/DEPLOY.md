# 智慧分身 · 部署指南

> 本文档覆盖本地、Docker、云端（Render / Railway / 任意 VPS）三种部署方式。
> 首次体验推荐 **dry-run 模式**：零外部依赖、零 API Key，完整跑通「记忆仓库 + Chat 中枢 + Skill/MCP」全链路。

---

## 0. 两种运行模式

| 模式 | 依赖 | 体验 |
| --- | --- | --- |
| **dry-run** | 仅 Python 核心依赖 | 框架全链路可跑：Skill 路由、记忆检索、权限投影、审计；大模型返回占位提示 |
| **完整模式** | DeepSeek API Key +（可选）本地嵌入/转写模型 | 真实智能：语义检索、记忆提炼、故事生成、复盘报告 |

切换方式：设置环境变量 `SMART_AVATAR_CONFIG` 指向不同配置文件。

- `config/app.dryrun.json` — dry-run（默认用于快速体验与云端 Demo）
- `config/app.json` — 完整模式（DeepSeek + bge-large-zh + faster-whisper）

---

## 1. 本地运行

```bash
git clone https://github.com/sunjunjie12323/smart-clone.git
cd smart-clone
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]

# dry-run 体验
SMART_AVATAR_CONFIG=config/app.dryrun.json python -m uvicorn smart_avatar.app:app --port 8000

# 或完整模式
export DEEPSEEK_API_KEY=sk-your-key
export HF_ENDPOINT=https://hf-mirror.com   # 国内下载嵌入模型镜像
pip install -e .[embedding,asr]
python -m uvicorn smart_avatar.app:app --port 8000
```

访问 http://localhost:8000 。

---

## 2. Docker

```bash
docker build -t smart-clone .
docker run -d -p 8000:8000 \
  -e SMART_AVATAR_CONFIG=config/app.dryrun.json \
  -v $(pwd)/data:/app/data \
  --name smart-clone smart-clone
```

接入真实模型时追加 `-e DEEPSEEK_API_KEY=...` 并改用 `config/app.json`。

### docker-compose（含数据持久化）

```yaml
version: "3.9"
services:
  smart-clone:
    build: .
    ports: ["8000:8000"]
    environment:
      SMART_AVATAR_CONFIG: config/app.dryrun.json
      # DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

---

## 3. Render.com（免费 · 推荐云端 Demo）

仓库内置 `render.yaml`（Blueprint）。

1. Fork / 使用本仓库（需公开）。
2. 打开 [Render Dashboard](https://dashboard.render.com) → **New +** → **Blueprint**。
3. 连接仓库 `sunjunjie12323/smart-clone`，Render 自动识别 `render.yaml`。
4. 部署完成后获得公开地址 `https://smart-clone.onrender.com`。
5. （可选）在 **Environment** 中填 `DEEPSEEK_API_KEY` 并把 `SMART_AVATAR_CONFIG` 改为 `config/app.json` 启用真实推理。

> 免费实例无磁盘持久化，`data/` 重启即重置 —— 适合 Demo，不适合长期记忆。
> 冷启动约 30s（免费实例休眠后首次访问）。

---

## 4. Railway / Fly.io

**Railway**：`railway up`，或在 Dashboard 连接 GitHub 仓库，Start Command 设为
`python -m uvicorn smart_avatar.app:app --host 0.0.0.0 --port $PORT`，加环境变量 `SMART_AVATAR_CONFIG=config/app.dryrun.json`。

**Fly.io**：

```bash
fly launch --dockerfile Dockerfile
fly secrets set SMART_AVATAR_CONFIG=config/app.dryrun.json
fly deploy
```

---

## 5. 任意 VPS（systemd）

```ini
# /etc/systemd/system/smart-clone.service
[Unit]
Description=Smart Clone (Memory OS)
After=network.target

[Service]
WorkingDirectory=/opt/smart-clone
Environment=SMART_AVATAR_CONFIG=config/app.dryrun.json
ExecStart=/opt/smart-clone/.venv/bin/python -m uvicorn smart_avatar.app:app --host 0.0.0.0 --port 8000
Restart=always
User=www-data

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now smart-clone
```

前置 Nginx/Caddy 反向代理 80/443 → 8000 即可绑定域名。

---

## 6. 健康检查与排错

| 检查 | 命令 |
| --- | --- |
| 存活 | `curl http://HOST:8000/health` → `{"status":"ok"}` |
| 配置 | `curl http://HOST:8000/api/v1/config` |
| API 文档 | 浏览器打开 `http://HOST:8000/docs` |

常见问题：
- **Chat 报 500 / 提示 sentence-transformers 未安装** → 当前为 `local` 嵌入但未装依赖。改用 dry-run 配置，或 `pip install -e .[embedding]`。
- **记忆提炼失败：API Key 未设置** → 未配置 `DEEPSEEK_API_KEY`。dry-run 模式下属预期（返回占位）。
- **端口占用** → 更换 `--port`，或 `lsof -ti:8000 | xargs kill`。

---

## 7. 隐私与数据

- 原始音频、转写全文默认仅存本地 `data/`，不上传云端。
- 数据库为本地 SQLite（`data/smart_avatar.db`），用户可随时导出（`GET /api/v1/export`）或一键清除（`DELETE /api/v1/memories`）。
- 详见 [PRIVACY.md](PRIVACY.md)。
