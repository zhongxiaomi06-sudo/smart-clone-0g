# 商业级运行与上线清单

这份清单面向后续商业化部署，重点是安全、可观测、配置隔离和可扩展运营。

## 环境变量

| 变量 | 作用 | 建议 |
| --- | --- | --- |
| `SMART_AVATAR_CONFIG` | 指定配置文件路径 | 不同环境使用不同配置 |
| `SMART_AVATAR_API_KEY` | API Key 鉴权密钥 | 生产环境必须设置强随机值 |

## API 安全

当前框架已支持：

- `x-api-key` 可选鉴权。
- `x-request-id` 请求追踪。
- 基础安全响应头。
- 简单内存限流。
- 统一错误响应结构。
- `/api/v1` 版本化路由。
- `/api` 兼容旧路由。
- `/` 基础 Web 控制台。

生产建议：

- 开启 `security.api_key_enabled`。
- 将 `rate_limit.requests_per_minute` 调整为符合业务流量的值。
- 在网关层增加 HTTPS、WAF、IP 黑白名单和更强限流。
- 不把 `data/*.db` 打包进镜像。
- 对 `data/` 做加密磁盘或专用密钥管理。
- 如果部署公网访问，建议在网关层给 `/` 和 `/static` 增加访问控制。

## Docker 运行

```bash
docker build -t smart-avatar .
docker run --rm -p 8000:8000 \
  -e SMART_AVATAR_API_KEY=change-me \
  -v smart-avatar-data:/app/data \
  smart-avatar
```

如果生产环境开启 API Key，需要把 `config/app.json` 中的 `security.api_key_enabled` 设置为 `true`。

## 错误响应格式

所有框架级错误都应保持统一结构：

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "request_id": "..."
  }
}
```

## 商业化前必须补齐

- 真实用户体系和租户隔离。
- 更强的密钥管理和数据加密。
- 正式向量数据库或可替换检索层。
- 真实 LLM Provider 适配器。
- 完整 MCP Server 调用和工具权限审批。
- 数据导出、删除、备份和恢复流程。
- 前端权限提示和上传前预览。
- 合规文档：隐私政策、数据处理协议、录音与健康数据提示。
