from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from starlette.responses import JSONResponse

from .audit import AuditService
from .chat import ChatOrchestrator
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
from .mcp import McpGateway
from .models import create_model_client
from .permissions import PermissionService
from .security import RequestSecurityMiddleware
from .skills import SkillRegistry
from .storage import SQLiteStore
from .transcribe import MemoryExtractor, create_transcriber
from .embeddings import create_embedding_client


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
) -> TranscriptionResult:
    """执行转写 + 自动提炼的完整闭环。

    遵循设计文档 5.1:本地转写 → 脱敏提炼 → 写入记忆仓库。
    任何步骤失败都会回写到录音记录的 transcript_status / transcript_error,
    不影响录音本身已入库的事实。
    """
    recording = store.get_recording(recording_id)
    if recording is None:
        return TranscriptionResult(
            recording_id=recording_id,
            status="failed",
            error="recording not found",
        )

    recording.transcript_status = "running"
    store.add_recording(recording)

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
        store.add_recording(recording)
        audit.record("recording.transcribe", recording.id, {"error": str(exc)})
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
        store.add_recording(recording)
        audit.record(
            "recording.transcribe",
            recording.id,
            {
                "provider": result.provider,
                "language": result.language,
                "length": len(result.transcript),
            },
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
                    saved = store.add_memory(card)
                    new_ids.append(saved.id)
                if new_ids:
                    recording.extracted_memory_ids = list(
                        dict.fromkeys([*recording.extracted_memory_ids, *new_ids])
                    )
                    store.add_recording(recording)
                    audit.record(
                        "recording.extract",
                        recording.id,
                        {"memory_ids": new_ids, "count": len(new_ids)},
                    )
                result.extracted_memory_ids = new_ids
            except Exception as extract_exc:  # noqa: BLE001
                # 提炼失败:转写已成功,记录提炼错误,不影响转写结果
                audit.record(
                    "recording.extract_failed",
                    recording.id,
                    {"error": str(extract_exc)},
                )
                result.extracted_memory_ids = []
                result.error = f"转写成功但记忆提炼失败:{extract_exc}"
    else:
        recording.transcript_status = "failed"
        recording.transcript_error = result.error or "transcription returned no text"
        store.add_recording(recording)
        audit.record(
            "recording.transcribe",
            recording.id,
            {"error": recording.transcript_error},
        )

    return result


def create_app(config: AppConfig | None = None) -> FastAPI:
    config = config or load_config()
    embedding_client = create_embedding_client(config.embedding)
    store = SQLiteStore(resolve_path(config.database_path), embedding_client=embedding_client)
    audit = AuditService(store)
    permissions = PermissionService(store)
    credentials = CredentialService(store, audit)
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

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "app": config.app_name}

    @api.post("/memories", response_model=MemoryCard)
    def create_memory(card: MemoryCard) -> MemoryCard:
        saved = store.add_memory(card)
        audit.record("memory.create", saved.id, {"privacy_level": saved.privacy_level})
        return saved

    @api.get("/memories", response_model=list[MemoryCard])
    def list_memories(limit: int = 50) -> list[MemoryCard]:
        return store.list_memories(limit=limit)

    @api.post("/memories/query", response_model=MemoryQueryResponse)
    def query_memories(query: MemoryQuery) -> MemoryQueryResponse:
        cards = store.query_memories(query)
        return MemoryQueryResponse(
            memory_cards=cards,
            citations=[
                Citation(source_type="memory", source_id=card.id, summary=card.event_summary)
                for card in cards
            ],
        )

    @api.post("/states", response_model=StateCard)
    def create_state(card: StateCard) -> StateCard:
        saved = store.add_state(card)
        audit.record("state.create", saved.id, {"risk_level": saved.risk_level})
        return saved

    @api.get("/states", response_model=list[StateCard])
    def list_states(limit: int = 50) -> list[StateCard]:
        return store.list_states(limit=limit)

    @api.post("/chat", response_model=ChatResponse)
    def chat_endpoint(request: ChatRequest) -> ChatResponse:
        return chat.handle(request)

    @api.get("/skills", response_model=list[SkillManifest])
    def list_skills() -> list[SkillManifest]:
        return skills.list()

    @api.post("/skills/{skill_name}/run", response_model=SkillRunResult)
    def run_skill(skill_name: str, request: SkillRunRequest) -> SkillRunResult:
        result = skills.run(skill_name, request)
        if result.status == "not_found":
            raise HTTPException(status_code=404, detail="Skill not found")
        return result

    @api.post("/tools/call", response_model=ToolCallResult)
    def call_tool(request: ToolCallRequest) -> ToolCallResult:
        return mcp.call(request)

    @api.get("/tools", response_model=list[ToolManifest])
    def list_tools() -> list[ToolManifest]:
        return mcp.registry.list()

    @api.post("/permissions/grants", response_model=PermissionGrant)
    def grant_permission(grant: PermissionGrant) -> PermissionGrant:
        saved = permissions.grant(grant.target, grant.scope, grant.expires_at)
        audit.record("permission.grant", saved.target, {"scope": saved.scope})
        return saved

    @api.post("/permissions/{grant_id}/revoke", response_model=PermissionGrant)
    def revoke_permission(grant_id: str) -> PermissionGrant:
        revoked = store.revoke_permission(grant_id, utc_now())
        if revoked is None:
            raise HTTPException(status_code=404, detail="Permission grant not found")
        audit.record("permission.revoke", revoked.target, {"permission_id": revoked.id})
        return revoked

    @api.get("/audit", response_model=list[AuditEvent])
    def list_audit(limit: int = 100) -> list[AuditEvent]:
        return store.list_audit_events(limit=limit)

    @api.post("/credentials/hash", response_model=CredentialRecord)
    def create_hash_credential(request: CredentialCreateRequest) -> CredentialRecord:
        return credentials.create_hash_credential(request)

    @api.get("/credentials", response_model=list[CredentialRecord])
    def list_credentials(
        subject_type: str | None = None,
        subject_id: str | None = None,
        limit: int = 100,
    ) -> list[CredentialRecord]:
        return store.list_credentials(
            subject_type=subject_type,
            subject_id=subject_id,
            limit=limit,
        )

    # ---- 记忆卡片 CRUD(设计 6 隐私红线:用户必须能删除任意记忆卡片)----
    @api.get("/memories/{memory_id}", response_model=MemoryCard)
    def get_memory(memory_id: str) -> MemoryCard:
        card = store.get_memory(memory_id)
        if card is None:
            raise HTTPException(status_code=404, detail="Memory not found")
        return card

    @api.put("/memories/{memory_id}", response_model=MemoryCard)
    def update_memory(memory_id: str, card: MemoryCard) -> MemoryCard:
        if memory_id != card.id:
            raise HTTPException(status_code=400, detail="ID 不匹配")
        saved = store.add_memory(card)
        audit.record("memory.update", saved.id, {"privacy_level": saved.privacy_level})
        return saved

    @api.delete("/memories/{memory_id}", response_model=MemoryCard)
    def delete_memory(memory_id: str) -> MemoryCard:
        card = store.delete_memory(memory_id)
        if card is None:
            raise HTTPException(status_code=404, detail="Memory not found")
        audit.record("memory.delete", memory_id, {"event_summary": card.event_summary})
        return card

    # ---- 状态卡片查询(设计 5.4 StateQuery)----
    @api.get("/states/query", response_model=list[StateCard])
    def query_states(
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
    ) -> list[StateCard]:
        return store.query_states(date_from=date_from, date_to=date_to, limit=limit)

    # ---- 文本提炼接口(设计 5.1:手动文本输入 → 脱敏提炼 → 记忆卡片)----
    @api.post("/memories/extract", response_model=MemoryExtractionResult)
    def extract_memories_from_text(
        request: MemoryExtractionRequest,
    ) -> MemoryExtractionResult:
        """从手动输入的文本中提炼记忆卡片。

        遵循设计 5.1:滑窗内容提炼 + 实体脱敏替换。
        text 字段直接传入文本内容;或通过 recording_id 引用已转写的录音。
        """
        # 确定要提炼的文本来源
        text_content = request.text
        source_id = "text_input"

        if not text_content and request.recording_id:
            existing = store.get_recording(request.recording_id)
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
            saved = store.add_memory(card)
            saved_cards.append(saved)
            new_ids.append(saved.id)
        if new_ids:
            audit.record(
                "memory.extract_text",
                source_id,
                {"memory_ids": new_ids, "count": len(new_ids)},
            )
        return MemoryExtractionResult(
            recording_id=source_id,
            memory_cards=saved_cards,
            provider=config.model.provider,
        )

    # ---- 数据导出(设计 6 隐私红线:用户可导出自己的数据)----
    @api.get("/export")
    def export_data():
        import json as _json  # noqa: PLC0415

        memories = store.list_memories(limit=10000)
        states = store.list_states(limit=10000)
        recordings = store.list_recordings(limit=10000)
        audits = store.list_audit_events(limit=10000)
        data = {
            "exported_at": utc_now(),
            "memories": [card.model_dump() for card in memories],
            "states": [card.model_dump() for card in states],
            "recordings": [
                {
                    **rec.model_dump(exclude={"storage_path"}),
                    "transcript": rec.transcript,
                }
                for rec in recordings
            ],
            "audit_events": [event.model_dump() for event in audits],
        }
        return JSONResponse(
            content=data,
            headers={
                "Content-Disposition": "attachment; filename=smart_avatar_export.json"
            },
        )

    # ---- 清除所有记忆(设计 6 隐私红线:用户可一键清除)----
    @api.delete("/memories")
    def clear_all_memories():
        count = 0
        cards = store.list_memories(limit=100000)
        for card in cards:
            store.delete_memory(card.id)
            count += 1
        audit.record("memory.clear_all", "all", {"deleted_count": count})
        return {"deleted_count": count, "message": "所有记忆卡片已清除。"}

    # ---- 录音采集与全天语音记忆存储 ----
    # 遵循设计文档 5.1:原始音频默认只保留在本地,转写后提炼为脱敏记忆卡片。
    @api.post("/recordings", response_model=AudioRecording)
    async def upload_recording(
        file: UploadFile = File(...),
        recorded_at: str | None = Form(None),
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
        content = await file.read()
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
        store.add_recording(recording)
        audit.record(
            "recording.upload",
            recording.id,
            {"file_name": recording.file_name, "size_bytes": recording.size_bytes},
        )

        # 上传后自动转写 + 提炼(遵循 5.1 闭环),失败不影响录音入库
        if config.transcription.auto_extract:
            _run_transcription_pipeline(
                recording_id=recording.id,
                store=store,
                transcriber=transcriber,
                extractor=extractor,
                recordings_dir=recordings_dir,
                config=config,
                audit=audit,
                language=config.transcription.default_language,
            )
        return store.get_recording(recording.id) or recording

    @api.get("/recordings", response_model=list[AudioRecording])
    def list_recordings(limit: int = 100) -> list[AudioRecording]:
        return store.list_recordings(limit=limit)

    @api.get("/recordings/{recording_id}", response_model=AudioRecording)
    def get_recording(recording_id: str) -> AudioRecording:
        recording = store.get_recording(recording_id)
        if recording is None:
            raise HTTPException(status_code=404, detail="Recording not found")
        return recording

    @api.post("/recordings/{recording_id}/transcribe", response_model=TranscriptionResult)
    def transcribe_recording(
        recording_id: str,
        request: TranscriptionRequest,
    ) -> TranscriptionResult:
        recording = store.get_recording(recording_id)
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
        )
        return result

    @api.post(
        "/recordings/{recording_id}/extract",
        response_model=MemoryExtractionResult,
    )
    def extract_memories(
        recording_id: str,
        request: MemoryExtractionRequest,
    ) -> MemoryExtractionResult:
        recording = store.get_recording(recording_id)
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
            saved = store.add_memory(card)
            saved_cards.append(saved)
            new_ids.append(saved.id)
        if new_ids:
            recording.extracted_memory_ids = list(
                dict.fromkeys([*recording.extracted_memory_ids, *new_ids])
            )
            store.add_recording(recording)
            audit.record(
                "recording.extract",
                recording.id,
                {"memory_ids": new_ids, "count": len(new_ids)},
            )
        return MemoryExtractionResult(
            recording_id=recording_id,
            memory_cards=saved_cards,
            provider=config.model.provider,
        )

    @api.delete("/recordings/{recording_id}", response_model=AudioRecording)
    def delete_recording(recording_id: str) -> AudioRecording:
        recording = store.delete_recording(recording_id)
        if recording is None:
            raise HTTPException(status_code=404, detail="Recording not found")
        # 同步删除本地原始音频文件(遵循隐私红线:用户可一键删除)
        try:
            path = resolve_path(recording.storage_path) if recording.storage_path else None
            if path and path.exists():
                path.unlink()
        except OSError:
            pass
        audit.record("recording.delete", recording.id, {"file_name": recording.file_name})
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

    return app


app = create_app()
