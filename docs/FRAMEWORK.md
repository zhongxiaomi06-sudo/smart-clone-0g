# 应用底层框架说明

当前实现把“智慧分身”拆成一个可扩展应用底座，而不是把故事生成、健康分析或某个具体场景写死进核心代码。

## 运行方式

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
python -m uvicorn smart_avatar.app:app --reload
```

启动后访问：

- `GET /health`
- `GET /`
- `GET /docs`

## 分层结构

| 层 | 文件 | 职责 |
| --- | --- | --- |
| API 层 | `src/smart_avatar/app.py` | 暴露 HTTP 接口，组装服务 |
| Web 层 | `web/` | 静态应用控制台，不依赖前端构建链 |
| Domain 层 | `src/smart_avatar/domain.py` | 统一请求、响应和领域模型 |
| Storage 层 | `src/smart_avatar/storage.py` | SQLite 本地存储适配器 |
| Chat 层 | `src/smart_avatar/chat.py` | 主入口，判断直接回答或调用 Skill |
| Skill 层 | `src/smart_avatar/skills.py` | 加载 Skill 配置、权限检查、上下文组装 |
| MCP 层 | `src/smart_avatar/mcp.py` | 外部工具接口网关，目前是安全占位实现 |
| Permission 层 | `src/smart_avatar/permissions.py` | 授权创建、撤销和范围校验 |
| Audit 层 | `src/smart_avatar/audit.py` | 记录记忆查询、Skill 调用、权限变化 |
| Privacy 层 | `src/smart_avatar/privacy.py` | 按 Skill 声明字段投影上下文 |
| Credential 层 | `src/smart_avatar/credentials.py` | 生成本地哈希凭证，为链上证明预留 |
| Model 层 | `src/smart_avatar/models.py` | 模型提供商抽象，当前默认 dry-run |

## 核心原则

- Chat 是主入口，Skill 是可插拔能力。
- 核心代码不识别“故事”这种具体业务，只根据 Skill manifest 的触发词和权限运行。
- MCP 工具默认不可用，需要显式注册适配器后才能调用。
- Skill 读取记忆必须经过权限确认或权限 token。
- 所有 Skill/MCP 调用都应进入审计日志。

更完整的需求映射见 `docs/REQUIREMENTS_ALIGNMENT.md`。

## 配置入口

主配置文件位于 `config/app.json`：

```json
{
  "database_path": "data/smart_avatar.db",
  "skills_dir": "skills",
  "tools_dir": "tools",
  "web_dir": "web",
  "api": {
    "prefix": "/api/v1",
    "legacy_prefix_enabled": true
  },
  "security": {
    "api_key_enabled": false,
    "api_key_env": "SMART_AVATAR_API_KEY",
    "public_paths": ["/", "/static", "/health", "/docs", "/openapi.json"]
  },
  "rate_limit": {
    "enabled": true,
    "requests_per_minute": 120
  },
  "model": {
    "provider": "dry_run",
    "default_model": "dry-run",
    "base_url": null,
    "api_key_env": null,
    "timeout_seconds": 60
  },
  "privacy": {
    "require_skill_confirmation": true,
    "allow_raw_memory_to_tools": false,
    "audit_all_tool_calls": true
  }
}
```

后续替换模型、存储位置、Skill 目录、工具目录、安全策略或 API 前缀时，优先改配置，不改核心服务代码。

## 已有接口

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `POST` | `/api/v1/memories` | 创建脱敏记忆卡片 |
| `GET` | `/api/v1/memories` | 列出记忆卡片 |
| `POST` | `/api/v1/memories/query` | 查询记忆仓库 |
| `POST` | `/api/v1/states` | 创建状态卡片 |
| `GET` | `/api/v1/states` | 列出状态卡片 |
| `POST` | `/api/v1/chat` | Chat 主入口 |
| `GET` | `/api/v1/skills` | 查看已注册 Skill |
| `POST` | `/api/v1/skills/{skill_name}/run` | 运行指定 Skill |
| `GET` | `/api/v1/tools` | 查看已注册 MCP/工具 manifest |
| `POST` | `/api/v1/tools/call` | 调用 MCP 工具网关 |
| `POST` | `/api/v1/permissions/grants` | 创建授权 |
| `POST` | `/api/v1/permissions/{grant_id}/revoke` | 撤销授权 |
| `GET` | `/api/v1/audit` | 查看审计日志 |
| `POST` | `/api/v1/credentials/hash` | 为本地内容生成哈希凭证 |
| `GET` | `/api/v1/credentials` | 查看本地凭证记录 |

默认也保留 `/api/...` 兼容路由，可通过 `api.legacy_prefix_enabled` 关闭。

## 添加一个 Skill

新增目录：

```text
skills/my_skill/
  skill.json
  prompt.md
```

`skill.json` 最小结构：

```json
{
  "name": "my_skill",
  "display_name": "我的 Skill",
  "type": "skill",
  "description": "这个 Skill 做什么。",
  "triggers": ["关键词"],
  "entry": {
    "kind": "prompt_template",
    "prompt_path": "prompt.md"
  },
  "memory_scope": {
    "default_time_range": null,
    "allowed_fields": ["event_summary", "insight"],
    "requires_user_confirm": true
  },
  "permissions": ["memory:read:desensitized"],
  "output_schema": ["result"]
}
```

核心代码不需要修改。Chat 中枢会根据 `triggers` 自动匹配，也可以通过 `/api/skills/{skill_name}/run` 指定运行。

## 当前内置示例

| Skill | 位置 | 说明 |
| --- | --- | --- |
| `daily_story` | `skills/daily_story` | 示例故事生成 Skill |
| `weekly_review` | `skills/weekly_review` | 示例周复盘 Skill |

## 添加一个 MCP 工具

新增目录：

```text
tools/my_tool/
  tool.json
```

`tool.json` 最小结构：

```json
{
  "name": "my_tool",
  "display_name": "我的工具",
  "description": "这个工具做什么。",
  "enabled": false,
  "entry": {
    "kind": "dry_run",
    "handler": null
  },
  "permissions": ["tool:my_tool:read"],
  "input_schema": {
    "type": "object",
    "properties": {}
  }
}
```

工具默认建议保持 `enabled: false`。只有当权限、输入预览、审计和适配器都准备好时，才开启真实调用。

## 权限调用方式

运行 Skill 或 MCP 工具前，可以先创建授权：

```json
{
  "target": "daily_story",
  "scope": ["memory:read:desensitized", "story:write"],
  "expires_at": null
}
```

返回的 `id` 可以作为 `permission_token` 传给：

- `POST /api/chat`
- `POST /api/v1/chat`
- `POST /api/v1/skills/{skill_name}/run`
- `POST /api/v1/tools/call`

如果只是本地 Demo，也可以在请求中传 `user_confirmed: true` 来模拟用户确认。

## 本地哈希凭证

当前 Web3 相关能力只做本地哈希凭证，不接真实链。用法是把需要证明的内容传给：

```json
{
  "subject_type": "memory",
  "subject_id": "mem_xxx",
  "payload": {
    "event_summary": "脱敏后的事件摘要"
  },
  "metadata": {
    "purpose": "existence_proof"
  }
}
```

系统会保存 SHA-256 摘要和本地审计记录。注意：这里仍然不应传入原始音频、原始文本、身体明细或任何隐私明文。

## 下一步扩展点

- 把 `DryRunModelClient` 替换为真实模型提供商适配器。
- 把 `SQLiteStore.query_memories` 替换为向量检索实现。
- 给 `McpGateway` 增加真实 MCP Server 调用。
- 给 Skill 增加版本管理、输入 schema 校验和输出 schema 校验。
- 增加 Web3 哈希凭证服务，但仍保持隐私明文不上链。
