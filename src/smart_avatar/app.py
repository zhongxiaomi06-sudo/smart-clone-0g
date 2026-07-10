from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    UploadFile,
    File,
    Form,
)
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from starlette.responses import JSONResponse
from starlette.responses import StreamingResponse

from .audit import AuditService
from .auth import AuthService, AuthResponse, LoginRequest, RegisterRequest
from .chat import ChatOrchestrator
from .cleanup import cleanup_expired_recordings
from .config import AppConfig, load_config, resolve_path
from .credentials import CredentialService
from .domain import (
    AudioRecording,
    AuditEvent,
    ChatRequest,
    ChatResponse,
    Citation,
    CredentialCreateRequest,
    CredentialRecord,
    MemoryCard,
    MemoryExtractionRequest,
    MemoryExtractionResult,
    MemoryQuery,
    MemoryQueryResponse,
    PermissionGrant,
    SkillManifest,
    SkillRunRequest,
    SkillRunResult,
    StateCard,
    ToolCallRequest,
    ToolCallResult,
    ToolManifest,
    TranscriptionRequest,
    TranscriptionResult,
    utc_now,
)
from .logging_config import get_request_logger, setup_logging
from .mcp import McpGateway
from .models import create_model_client
from .permissions import PermissionService
from .security import RequestSecurityMiddleware
from .skills import SkillRegistry
from .storage import SQLiteStore
from .transcribe import MemoryExtractor, create_transcriber
from .embeddings import create_embedding_client

import json as json_module  # noqa: F401  保留供流式导出等场景使用


_MIME_SUFFIX = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/m4a": ".m4a",
    "application/octet-stream": ".webm",
}


def _guess_suffix(mime_type: str, filename: str | None) -> str:
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
        if ext in {".webm", ".ogg", ".wav", ".mp3", ".m4a", ".mp4"}:
            return ext
    return _MIME_SUFFIX.get(mime_type, ".webm")


def _run_transcription_pipeline(
    *,
    recording_id: str,
    store: SQLiteStore,
    transcriber,
    extractor: MemoryExtractor,
    recordings_dir,
    config: AppConfig,
    audit: AuditService,
    language: str | None,
    auto_extract: bool | None = None,
    user_id: str = "default",
) -> TranscriptionResult:
    """执行转写 + 自动提炼的完整闭环。

    遵循设计文档 5.1:本地转写 → 脱敏提炼 → 写入记忆仓库。
    任何步骤失败都会回写到录音记录的 transcript_status / transcript_error,
    不影响录音本身已入库的事实。
    """
    recording = store.get_recording(recording_id, user_id=user_id)
    if recording is None:
        return TranscriptionResult(
            recording_id=recording_id,
            status="failed",
            error="recording not found",
        )

    recording.transcript_status = "running"
    store.add_recording(recording, user_id=user_id)

    try:
        path = (
            recordings_dir / Path(recording.storage_path).name
            if recording.storage_path
            else None
        )
        if path is None or not path.exists():
            raise FileNotFoundError(f"音频文件不存在:{recording.storage_path}")
        result = transcriber.transcribe(path, language=language)
        result.recording_id = recording_id
    except Exception as exc:  # noqa: BLE001
        recording.transcript_status = "failed"
        recording.transcript_error = str(exc)
        store.add_recording(recording, user_id=user_id)
        audit.record(
            "recording.transcribe", recording.id, {"error": str(exc)}, user_id=user_id
        )
        return TranscriptionResult(
            recording_id=recording_id,
            status="failed",
            error=str(exc),
            provider=getattr(transcriber, "provider_name", None),
        )

    if result.status == "completed" and result.transcript is not None:
        recording.transcript = result.transcript
        recording.transcript_language = result.language
        recording.transcript_provider = result.provider
        recording.transcript_error = None
        recording.transcript_status = "completed"
        store.add_recording(recording, user_id=user_id)
        audit.record(
            "recording.transcribe",
            recording.id,
            {
                "provider": result.provider,
                "language": result.language,
                "length": len(result.transcript),
            },
            user_id=user_id,
        )

        should_extract = (
            auto_extract if auto_extract is not None else config.transcription.auto_extract
        )
        if should_extract:
            try:
                cards = extractor.extract(
                    recording,
                    max_cards=config.transcription.max_cards_per_recording,
                    language=language,
                )
                new_ids: list[str] = []
                for card in cards:
                    saved = store.add_memory(card, user_id=user_id)
                    new_ids.append(saved.id)
                if new_ids:
                    recording.extracted_memory_ids = list(
                        dict.fromkeys([*recording.extracted_memory_ids, *new_ids])
                    )
                    store.add_recording(recording, user_id=user_id)
                    audit.record(
                        "recording.extract",
                        recording.id,
                        {"memory_ids": new_ids, "count": len(new_ids)},
                        user_id=user_id,
                    )
                result.extracted_memory_ids = new_ids
            except Exception as extract_exc:  # noqa: BLE001
                # 提炼失败:转写已成功,记录提炼错误,不影响转写结果
                audit.record(
                    "recording.extract_failed",
                    recording.id,
                    {"error": str(extract_exc)},
                    user_id=user_id,
                )
                result.extracted_memory_ids = []
                result.error = f"转写成功但记忆提炼失败:{extract_exc}"
    else:
        recording.transcript_status = "failed"
        recording.transcript_error = result.error or "transcription returned no text"
        store.add_recording(recording, user_id=user_id)
        audit.record(
            "recording.transcribe",
            recording.id,
            {"error": recording.transcript_error},
            user_id=user_id,
        )

    return result


def create_app(config: AppConfig | None = None) -> FastAPI:
    config = config or load_config()
    # 初始化结构化日志
    setup_logging(config.environment.log_level)
    logger = logging.getLogger("smart_avatar.app")

    embedding_client = create_embedding_client(config.embedding)
    store = SQLiteStore(resolve_path(config.database_path), embedding_client=embedding_client)
    audit = AuditService(store)
    permissions = PermissionService(store)
    credentials = CredentialService(store, audit)

    # 认证服务
    jwt_secret = os.getenv(
        config.security.jwt_secret_env, "default-secret-change-in-production"
    )
    auth_service = AuthService(
        store=store,
        jwt_secret=jwt_secret,
        jwt_expire_minutes=config.security.jwt_expire_minutes,
    )

    model_client = create_model_client(config.model)
    skills = SkillRegistry(
        skills_dir=resolve_path(config.skills_dir),
        store=store,
        permissions=permissions,
        audit=audit,
        model_client=model_client,
        require_confirmation=config.privacy.require_skill_confirmation,
    )
    chat = ChatOrchestrator(
        store=store, skills=skills, audit=audit, model_client=model_client
    )
    mcp = McpGateway(
        tools_dir=resolve_path(config.tools_dir),
        audit=audit,
        permissions=permissions,
    )
    transcriber = create_transcriber(config.transcription)
    recordings_dir = resolve_path(config.recordings_dir)
    recordings_dir.mkdir(parents=True, exist_ok=True)
    extractor = MemoryExtractor(
        model_client=model_client,
        provider_name=config.model.provider,
    )

    app = FastAPI(title=config.app_name, version="0.1.0")
    app.add_middleware(
        RequestSecurityMiddleware,
        security=config.security,
        rate_limit=config.rate_limit,
    )
    api = APIRouter()

    # JWT 认证依赖
    security_scheme = HTTPBearer(auto_error=False)

    def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    ) -> str:
        """从 JWT token 提取用户 ID。未认证时返回 'default'（开发模式兼容）。"""
        if credentials is None:
            # 未提供 token,返回 default（向后兼容开发模式）
            return "default"
        token = credentials.credentials
        user_id = auth_service.verify_token(token)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_id

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "http_error",
                    "message": exc.detail,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed.",
                    "request_id": getattr(request.state, "request_id", None),
                    "details": exc.errors(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "unhandled.exception",
            extra={"request_id": request_id, "error": str(exc)},
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "服务器内部错误，请稍后重试。",
                    "request_id": request_id,
                }
            },
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "app": config.app_name}

    @app.get("/api/v1/config")
    def get_config() -> dict:
        """返回当前配置(脱敏,不含 API Key)。供前端设置页展示。"""
        return {
            "model": {
                "provider": config.model.provider,
                "default_model": config.model.default_model,
                "base_url": config.model.base_url,
            },
            "transcription": {
                "provider": config.transcription.provider,
                "model_size": config.transcription.model_size,
                "device": config.transcription.device,
                "default_language": config.transcription.default_language,
            },
            "embedding": {
                "provider": config.embedding.provider,
                "model_name": config.embedding.model_name,
                "dimension": config.embedding.dimension,
            },
            "privacy": {
                "require_skill_confirmation": config.privacy.require_skill_confirmation,
                "allow_raw_memory_to_tools": config.privacy.allow_raw_memory_to_tools,
                "audit_all_tool_calls": config.privacy.audit_all_tool_calls,
            },
        }

    # ---- 认证端点 ----
    @api.post("/auth/register", response_model=AuthResponse)
    def register(request: RegisterRequest) -> AuthResponse:
        try:
            return auth_service.register(request.email, request.password)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @api.post("/auth/login", response_model=AuthResponse)
    def login(request: LoginRequest) -> AuthResponse:
        try:
            return auth_service.login(request.email, request.password)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc))

    @api.post("/memories", response_model=MemoryCard)
    def create_memory(
        card: MemoryCard, user_id: str = Depends(get_current_user)
    ) -> MemoryCard:
        saved = store.add_memory(card, user_id=user_id)
        audit.record(
            "memory.create",
            saved.id,
            {"privacy_level": saved.privacy_level},
            user_id=user_id,
        )
        return saved

    @api.get("/memories", response_model=list[MemoryCard])
    def list_memories(
        limit: int = 50, user_id: str = Depends(get_current_user)
    ) -> list[MemoryCard]:
        return store.list_memories(limit=limit, user_id=user_id)

    @api.post("/memories/query", response_model=MemoryQueryResponse)
    def query_memories(
        query: MemoryQuery, user_id: str = Depends(get_current_user)
    ) -> MemoryQueryResponse:
        cards = store.query_memories(query, user_id=user_id)
        return MemoryQueryResponse(
            memory_cards=cards,
            citations=[
                Citation(source_type="memory", source_id=card.id, summary=card.event_summary)
                for card in cards
            ],
        )

    @api.post("/states", response_model=StateCard)
    def create_state(
        card: StateCard, user_id: str = Depends(get_current_user)
    ) -> StateCard:
        saved = store.add_state(card, user_id=user_id)
        audit.record(
            "state.create", saved.id, {"risk_level": saved.risk_level}, user_id=user_id
        )
        return saved

    @api.get("/states", response_model=list[StateCard])
    def list_states(
        limit: int = 50, user_id: str = Depends(get_current_user)
    ) -> list[StateCard]:
        return store.list_states(limit=limit, user_id=user_id)

    @api.post("/chat", response_model=ChatResponse)
    def chat_endpoint(
        request: ChatRequest, user_id: str = Depends(get_current_user)
    ) -> ChatResponse:
        return chat.handle(request, user_id=user_id)

    @api.get("/skills", response_model=list[SkillManifest])
    def list_skills(
        user_id: str = Depends(get_current_user),
    ) -> list[SkillManifest]:
        return skills.list()

    @api.post("/skills/{skill_name}/run", response_model=SkillRunResult)
    def run_skill(
        skill_name: str,
        request: SkillRunRequest,
        user_id: str = Depends(get_current_user),
    ) -> SkillRunResult:
        result = skills.run(skill_name, request)
        if result.status == "not_found":
            raise HTTPException(status_code=404, detail="Skill not found")
        return result

    @api.post("/tools/call", response_model=ToolCallResult)
    def call_tool(
        request: ToolCallRequest, user_id: str = Depends(get_current_user)
    ) -> ToolCallResult:
        return mcp.call(request)

    @api.get("/tools", response_model=list[ToolManifest])
    def list_tools(
        user_id: str = Depends(get_current_user),
    ) -> list[ToolManifest]:
        return mcp.registry.list()

    @api.post("/permissions/grants", response_model=PermissionGrant)
    def grant_permission(
        grant: PermissionGrant,
        user_id: str = Depends(get_current_user),
    ) -> PermissionGrant:
        saved = permissions.grant(
            grant.target, grant.scope, grant.expires_at, user_id=user_id
        )
        audit.record(
            "permission.grant", saved.target, {"scope": saved.scope}, user_id=user_id
        )
        return saved

    @api.get("/permissions", response_model=list[PermissionGrant])
    def list_permissions(
        target: str | None = None,
        user_id: str = Depends(get_current_user),
    ) -> list[PermissionGrant]:
        return store.list_permissions(target=target, user_id=user_id)

    @api.post("/permissions/{grant_id}/revoke", response_model=PermissionGrant)
    def revoke_permission(
        grant_id: str, user_id: str = Depends(get_current_user)
    ) -> PermissionGrant:
        revoked = store.revoke_permission(grant_id, utc_now())
        if revoked is None:
            raise HTTPException(status_code=404, detail="Permission grant not found")
        audit.record(
            "permission.revoke",
            revoked.target,
            {"permission_id": revoked.id},
            user_id=user_id,
        )
        return revoked

    @api.get("/audit", response_model=list[AuditEvent])
    def list_audit(
        limit: int = 100, user_id: str = Depends(get_current_user)
    ) -> list[AuditEvent]:
        return store.list_audit_events(limit=limit, user_id=user_id)

    @api.post("/credentials/hash", response_model=CredentialRecord)
    def create_hash_credential(
        request: CredentialCreateRequest,
        user_id: str = Depends(get_current_user),
    ) -> CredentialRecord:
        return credentials.create_hash_credential(request, user_id=user_id)

    @api.get("/credentials", response_model=list[CredentialRecord])
    def list_credentials(
        subject_type: str | None = None,
        subject_id: str | None = None,
        limit: int = 100,
        user_id: str = Depends(get_current_user),
    ) -> list[CredentialRecord]:
        return store.list_credentials(
            subject_type=subject_type,
            subject_id=subject_id,
            limit=limit,
            user_id=user_id,
        )

    # ---- 记忆卡片 CRUD(设计 6 隐私红线:用户必须能删除任意记忆卡片)----
    @api.get("/memories/{memory_id}", response_model=MemoryCard)
    def get_memory(
        memory_id: str, user_id: str = Depends(get_current_user)
    ) -> MemoryCard:
        card = store.get_memory(memory_id, user_id=user_id)
        if card is None:
            raise HTTPException(status_code=404, detail="Memory not found")
        return card

    @api.put("/memories/{memory_id}", response_model=MemoryCard)
    def update_memory(
        memory_id: str,
        card: MemoryCard,
        user_id: str = Depends(get_current_user),
    ) -> MemoryCard:
        if memory_id != card.id:
            raise HTTPException(status_code=400, detail="ID 不匹配")
        saved = store.add_memory(card, user_id=user_id)
        audit.record(
            "memory.update",
            saved.id,
            {"privacy_level": saved.privacy_level},
            user_id=user_id,
        )
        return saved

    @api.delete("/memories/{memory_id}", response_model=MemoryCard)
    def delete_memory(
        memory_id: str, user_id: str = Depends(get_current_user)
    ) -> MemoryCard:
        card = store.delete_memory(memory_id, user_id=user_id)
        if card is None:
            raise HTTPException(status_code=404, detail="Memory not found")
        audit.record(
            "memory.delete",
            memory_id,
            {"event_summary": card.event_summary},
            user_id=user_id,
        )
        return card

    # ---- 状态卡片查询(设计 5.4 StateQuery)----
    @api.get("/states/query", response_model=list[StateCard])
    def query_states(
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        user_id: str = Depends(get_current_user),
    ) -> list[StateCard]:
        return store.query_states(
            date_from=date_from, date_to=date_to, limit=limit, user_id=user_id
        )

    # ---- 文本提炼接口(设计 5.1:手动文本输入 → 脱敏提炼 → 记忆卡片)----
    @api.post("/memories/extract", response_model=MemoryExtractionResult)
    def extract_memories_from_text(
        request: MemoryExtractionRequest,
        user_id: str = Depends(get_current_user),
    ) -> MemoryExtractionResult:
        """从手动输入的文本中提炼记忆卡片。

        遵循设计 5.1:滑窗内容提炼 + 实体脱敏替换。
        text 字段直接传入文本内容;或通过 recording_id 引用已转写的录音。
        """
        # 确定要提炼的文本来源
        text_content = request.text
        source_id = "text_input"

        if not text_content and request.recording_id:
            existing = store.get_recording(request.recording_id, user_id=user_id)
            if existing and existing.transcript:
                text_content = existing.transcript
                source_id = request.recording_id

        if not text_content or not text_content.strip():
            return MemoryExtractionResult(
                recording_id=source_id,
                memory_cards=[],
                provider=config.model.provider,
                error="未提供可提炼的文本内容",
            )

        # 构造临时录音对象承载文本,复用提炼器
        from .domain import AudioRecording as _Recording  # noqa: PLC0415

        temp_recording = _Recording(
            id=source_id,
            file_name=source_id,
            storage_path="",
            transcript=text_content,
            recorded_at=utc_now(),
        )

        try:
            cards = extractor.extract(
                temp_recording,
                max_cards=request.max_cards,
                language=request.language,
            )
        except Exception as extract_exc:  # noqa: BLE001
            audit.record(
                "memory.extract_text_failed",
                source_id,
                {"error": str(extract_exc)},
                user_id=user_id,
            )
            return MemoryExtractionResult(
                recording_id=source_id,
                memory_cards=[],
                provider=config.model.provider,
                error=f"记忆提炼失败:{extract_exc}",
            )
        saved_cards: list[MemoryCard] = []
        new_ids: list[str] = []
        for card in cards:
            saved = store.add_memory(card, user_id=user_id)
            saved_cards.append(saved)
            new_ids.append(saved.id)
        if new_ids:
            audit.record(
                "memory.extract_text",
                source_id,
                {"memory_ids": new_ids, "count": len(new_ids)},
                user_id=user_id,
            )
        return MemoryExtractionResult(
            recording_id=source_id,
            memory_cards=saved_cards,
            provider=config.model.provider,
        )

    # ---- 数据导出(设计 6 隐私红线:用户可导出自己的数据)----
    @api.get("/export")
    def export_data(user_id: str = Depends(get_current_user)):
        def generate():
            yield '{"exported_at": "' + utc_now() + '", '
            yield '"memories": ['
            memories = store.list_memories(limit=10000, user_id=user_id)
            for i, card in enumerate(memories):
                if i > 0:
                    yield ", "
                yield card.model_dump_json()
            yield '], "states": ['
            states = store.list_states(limit=10000, user_id=user_id)
            for i, card in enumerate(states):
                if i > 0:
                    yield ", "
                yield card.model_dump_json()
            yield '], "recordings": ['
            recordings = store.list_recordings(limit=10000, user_id=user_id)
            for i, rec in enumerate(recordings):
                if i > 0:
                    yield ", "
                yield rec.model_dump_json(exclude={"storage_path"})
            yield '], "audit_events": ['
            audits = store.list_audit_events(limit=10000, user_id=user_id)
            for i, event in enumerate(audits):
                if i > 0:
                    yield ", "
                yield event.model_dump_json()
            yield ']}'

        return StreamingResponse(
            generate(),
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=smart_avatar_export.json"
            },
        )

    # ---- 清除所有记忆(设计 6 隐私红线:用户可一键清除)----
    @api.delete("/memories")
    def clear_all_memories(user_id: str = Depends(get_current_user)):
        count = store.clear_all_memories(user_id=user_id)
        audit.record(
            "memory.clear_all", "all", {"deleted_count": count}, user_id=user_id
        )
        return {"deleted_count": count, "message": "所有记忆卡片已清除。"}

    # ---- 录音采集与全天语音记忆存储 ----
    # 遵循设计文档 5.1:原始音频默认只保留在本地,转写后提炼为脱敏记忆卡片。
    @api.post("/recordings", response_model=AudioRecording)
    async def upload_recording(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        recorded_at: str | None = Form(None),
        user_id: str = Depends(get_current_user),
    ) -> AudioRecording:
        allowed_mime = {
            "audio/webm",
            "audio/ogg",
            "audio/wav",
            "audio/x-wav",
            "audio/mpeg",
            "audio/mp3",
            "audio/mp4",
            "audio/m4a",
            "application/octet-stream",
        }
        mime_type = file.content_type or "audio/webm"
        if mime_type not in allowed_mime:
            raise HTTPException(
                status_code=415,
                detail=f"不支持的音频类型:{mime_type}",
            )
        # 检查文件大小(先读取内容)
        content = await file.read()
        max_size = config.security.max_upload_size_mb * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"文件大小超过限制({config.security.max_upload_size_mb}MB)",
            )
        if not content:
            raise HTTPException(status_code=400, detail="音频文件为空。")

        suffix = _guess_suffix(mime_type, file.filename)
        recording = AudioRecording(
            file_name=file.filename or f"recording{suffix}",
            storage_path="",
            mime_type=mime_type,
            size_bytes=len(content),
            recorded_at=recorded_at or utc_now(),
            auto_delete_after_days=config.transcription.auto_delete_after_days,
        )
        storage_path = recordings_dir / f"{recording.id}{suffix}"
        storage_path.write_bytes(content)
        recording.storage_path = str(storage_path)
        store.add_recording(recording, user_id=user_id)
        audit.record(
            "recording.upload",
            recording.id,
            {"file_name": recording.file_name, "size_bytes": recording.size_bytes},
            user_id=user_id,
        )

        # 上传后自动转写 + 提炼(遵循 5.1 闭环),失败不影响录音入库
        # 使用 BackgroundTasks 异步执行,避免阻塞请求
        if config.transcription.auto_extract:
            background_tasks.add_task(
                _run_transcription_pipeline,
                recording_id=recording.id,
                store=store,
                transcriber=transcriber,
                extractor=extractor,
                recordings_dir=recordings_dir,
                config=config,
                audit=audit,
                language=config.transcription.default_language,
                user_id=user_id,
            )
        return store.get_recording(recording.id, user_id=user_id) or recording

    @api.get("/recordings", response_model=list[AudioRecording])
    def list_recordings(
        limit: int = 100, user_id: str = Depends(get_current_user)
    ) -> list[AudioRecording]:
        return store.list_recordings(limit=limit, user_id=user_id)

    @api.get("/recordings/{recording_id}", response_model=AudioRecording)
    def get_recording(
        recording_id: str, user_id: str = Depends(get_current_user)
    ) -> AudioRecording:
        recording = store.get_recording(recording_id, user_id=user_id)
        if recording is None:
            raise HTTPException(status_code=404, detail="Recording not found")
        return recording

    @api.post("/recordings/{recording_id}/transcribe", response_model=TranscriptionResult)
    def transcribe_recording(
        recording_id: str,
        request: TranscriptionRequest,
        user_id: str = Depends(get_current_user),
    ) -> TranscriptionResult:
        recording = store.get_recording(recording_id, user_id=user_id)
        if recording is None:
            raise HTTPException(status_code=404, detail="Recording not found")
        result = _run_transcription_pipeline(
            recording_id=recording_id,
            store=store,
            transcriber=transcriber,
            extractor=extractor,
            recordings_dir=recordings_dir,
            config=config,
            audit=audit,
            language=request.language or config.transcription.default_language,
            auto_extract=request.auto_extract,
            user_id=user_id,
        )
        return result

    @api.post(
        "/recordings/{recording_id}/extract",
        response_model=MemoryExtractionResult,
    )
    def extract_memories(
        recording_id: str,
        request: MemoryExtractionRequest,
        user_id: str = Depends(get_current_user),
    ) -> MemoryExtractionResult:
        recording = store.get_recording(recording_id, user_id=user_id)
        if recording is None:
            raise HTTPException(status_code=404, detail="Recording not found")
        if not recording.transcript:
            raise HTTPException(
                status_code=409,
                detail="录音尚未完成转写,请先调用 /recordings/{id}/transcribe。",
            )
        try:
            cards = extractor.extract(
                recording,
                max_cards=request.max_cards,
                language=request.language,
            )
        except Exception as extract_exc:  # noqa: BLE001
            audit.record(
                "recording.extract_failed",
                recording.id,
                {"error": str(extract_exc)},
                user_id=user_id,
            )
            return MemoryExtractionResult(
                recording_id=recording_id,
                memory_cards=[],
                provider=config.model.provider,
                error=f"记忆提炼失败:{extract_exc}",
            )
        saved_cards: list[MemoryCard] = []
        new_ids: list[str] = []
        for card in cards:
            saved = store.add_memory(card, user_id=user_id)
            saved_cards.append(saved)
            new_ids.append(saved.id)
        if new_ids:
            recording.extracted_memory_ids = list(
                dict.fromkeys([*recording.extracted_memory_ids, *new_ids])
            )
            store.add_recording(recording, user_id=user_id)
            audit.record(
                "recording.extract",
                recording.id,
                {"memory_ids": new_ids, "count": len(new_ids)},
                user_id=user_id,
            )
        return MemoryExtractionResult(
            recording_id=recording_id,
            memory_cards=saved_cards,
            provider=config.model.provider,
        )

    @api.delete("/recordings/{recording_id}", response_model=AudioRecording)
    def delete_recording(
        recording_id: str, user_id: str = Depends(get_current_user)
    ) -> AudioRecording:
        recording = store.delete_recording(recording_id, user_id=user_id)
        if recording is None:
            raise HTTPException(status_code=404, detail="Recording not found")
        # 同步删除本地原始音频文件(遵循隐私红线:用户可一键删除)
        try:
            path = resolve_path(recording.storage_path) if recording.storage_path else None
            if path and path.exists():
                path.unlink()
        except OSError:
            pass
        audit.record(
            "recording.delete",
            recording.id,
            {"file_name": recording.file_name},
            user_id=user_id,
        )
        return recording

    app.include_router(api, prefix=config.api.prefix)
    if config.api.legacy_prefix_enabled and config.api.prefix != "/api":
        app.include_router(api, prefix="/api")

    web_dir = resolve_path(config.web_dir)
    index_path = web_dir / "index.html"
    static_dir = web_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    if index_path.exists():

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(index_path)

    # 启动时执行过期录音清理
    try:
        result = cleanup_expired_recordings(store, recordings_dir, audit)
        if result["deleted"] > 0:
            logger.info("startup.cleanup", extra=result)
    except Exception as exc:
        logger.warning("startup.cleanup_failed", extra={"error": str(exc)})

    return app


app = create_app()
