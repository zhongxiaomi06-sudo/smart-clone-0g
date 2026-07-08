from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .config import TranscriptionConfig
from .domain import (
    AudioRecording,
    MemoryCard,
    TranscriptionResult,
)


class Transcriber(Protocol):
    """语音转写抽象。遵循设计文档 5.1:本地优先,可在端侧完成。"""

    provider_name: str

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: str | None = None,
    ) -> TranscriptionResult:
        ...


@dataclass(frozen=True)
class DryRunTranscriber:
    """占位转写器。未配置真实 ASR 时使用,返回提示文本而非真实转写。

    这样可以保证整个录音→转写→提炼→记忆卡片闭环在无模型环境下也能跑通,
    便于验证框架正确性。真实使用时应切换到 whisper_local 或其他 provider。
    """

    provider_name: str = "dry_run"

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: str | None = None,
    ) -> TranscriptionResult:
        return TranscriptionResult(
            recording_id="",
            status="completed",
            transcript=(
                f"[dry-run] 已收到音频文件 {audio_path.name},但未配置真实语音转写引擎。"
                "请在 config/app.json 中将 transcription.provider 设置为 whisper_local,"
                "并执行 pip install -e .[asr] 安装 faster-whisper 依赖后重试。"
            ),
            language=language or "zh",
            provider=self.provider_name,
        )


@dataclass(frozen=True)
class WhisperLocalTranscriber:
    """基于 faster-whisper 的本地转写器。

    模型默认从 HuggingFace 下载,首次使用需要联网。之后完全离线运行,
    符合设计文档"本地优先"和"原始音频不上传"的隐私原则。
    """

    model_size: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    provider_name: str = "whisper_local"

    def _load_model(self) -> Any:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper 未安装。请执行 pip install -e .[asr] 安装 ASR 依赖。"
            ) from exc

        return WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: str | None = None,
    ) -> TranscriptionResult:
        try:
            model = self._load_model()
            segments, info = model.transcribe(
                str(audio_path),
                language=language,
                vad_filter=True,
                beam_size=5,
            )
            text_parts: list[str] = []
            for segment in segments:
                text_parts.append(segment.text.strip())
            transcript = "".join(text_parts).strip()
            return TranscriptionResult(
                recording_id="",
                status="completed",
                transcript=transcript,
                language=info.language if info else language,
                provider=self.provider_name,
            )
        except Exception as exc:  # noqa: BLE001
            return TranscriptionResult(
                recording_id="",
                status="failed",
                error=str(exc),
                provider=self.provider_name,
            )


def create_transcriber(config: TranscriptionConfig) -> Transcriber:
    """根据配置创建转写器。provider 可选:dry_run / whisper_local。"""
    if config.provider == "whisper_local":
        return WhisperLocalTranscriber(
            model_size=config.model_size,
            device=config.device,
            compute_type=config.compute_type,
        )
    return DryRunTranscriber()


# ---------------------------------------------------------------------------
# 记忆提炼
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM_PROMPT = """你是本地隐私提炼器。你的任务是从用户当天录音转写文本中提取高价值生活片段,并输出结构化记忆卡片。

规则:
1. 不得输出真实人名、地名、公司名、账号、电话号码、精确地址或精确金额。
2. 所有实体必须替换为代号,例如"同事A""朋友B""常去的咖啡馆"。
3. 忽略无意义寒暄、重复语气词和无法形成记忆价值的内容。
4. 不编造文本中没有出现的信息。
5. 每张卡片只描述一个相对完整的事件或感受。

输出 JSON 数组,每个元素字段包括:
id、time_range、event_summary、emotion(label,intensity)、insight、personality_signals、entities(people,places)、privacy_level、source_type。
"""

EXTRACTION_USER_TEMPLATE = """以下是今天某段录音的转写文本,请提炼为最多 {max_cards} 张记忆卡片:

---
{transcript}
---

请按系统提示的规则输出 JSON 数组。"""


# 简单脱敏正则:手机号、身份证、银行卡、邮箱、精确金额
_PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")
_ID_CARD_PATTERN = re.compile(r"\d{17}[\dXx]")
_BANK_CARD_PATTERN = re.compile(r"\b\d{16,19}\b")
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_MONEY_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*(?:元|块钱|人民币|￥|¥)")


def rule_desensitize(text: str) -> str:
    """规则脱敏:dry-run 模式下的最低保障,真实模式应由模型完成脱敏。"""
    text = _PHONE_PATTERN.sub("[手机号]", text)
    text = _ID_CARD_PATTERN.sub("[身份证号]", text)
    text = _BANK_CARD_PATTERN.sub("[卡号]", text)
    text = _EMAIL_PATTERN.sub("[邮箱]", text)
    text = _MONEY_PATTERN.sub("[金额]", text)
    return text


def split_transcript(transcript: str, max_chars_per_chunk: int = 200) -> list[str]:
    """将转写文本按句号、换行切分为多个段落,每段不超过指定长度。"""
    if not transcript or not transcript.strip():
        return []
    raw_parts = re.split(r"[。\n!?！？]", transcript)
    parts: list[str] = []
    current: str = ""
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        if len(current) + len(part) + 1 <= max_chars_per_chunk:
            current = f"{current}。{part}" if current else part
        else:
            if current:
                parts.append(current)
            current = part
    if current:
        parts.append(current)
    return parts


@dataclass(frozen=True)
class MemoryExtractor:
    """从转写文本提炼记忆卡片。

    真实模型可用时按设计文档 11.1 提示词提炼;
    dry-run 模式下用规则切段 + 脱敏生成占位卡片,保证闭环可跑通。
    """

    model_client: Any
    provider_name: str = "dry_run"

    def extract(
        self,
        recording: AudioRecording,
        *,
        max_cards: int = 5,
        language: str | None = None,
    ) -> list[MemoryCard]:
        transcript = recording.transcript or ""
        if not transcript.strip():
            return []

        if self.provider_name == "dry_run":
            return self._extract_with_rules(transcript, recording, max_cards)
        return self._extract_with_model(transcript, recording, max_cards, language)

    def _extract_with_model(
        self,
        transcript: str,
        recording: AudioRecording,
        max_cards: int,
        language: str | None,
    ) -> list[MemoryCard]:
        user_prompt = EXTRACTION_USER_TEMPLATE.format(
            max_cards=max_cards,
            transcript=transcript,
        )
        try:
            raw = self.model_client.generate(
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            cards_data = self._parse_json_array(raw)
        except Exception:  # noqa: BLE001
            return self._extract_with_rules(transcript, recording, max_cards)

        cards: list[MemoryCard] = []
        for item in cards_data[:max_cards]:
            item.setdefault("source_type", "local_transcript")
            item.setdefault("privacy_level", "desensitized")
            try:
                cards.append(MemoryCard.model_validate(item))
            except Exception:  # noqa: BLE001
                continue
        return cards

    def _extract_with_rules(
        self,
        transcript: str,
        recording: AudioRecording,
        max_cards: int,
    ) -> list[MemoryCard]:
        """dry-run 模式下的规则提炼:切段 + 脱敏,生成占位记忆卡片。"""
        chunks = split_transcript(transcript)[:max_cards]
        cards: list[MemoryCard] = []
        for index, chunk in enumerate(chunks, start=1):
            safe_text = rule_desensitize(chunk)
            cards.append(
                MemoryCard(
                    time_range=recording.recorded_at,
                    event_summary=safe_text,
                    insight=None,
                    emotion=None,
                    personality_signals=[],
                    tags=["录音转写"],
                    entities={"people": [], "places": []},
                    privacy_level="desensitized",
                    source_type="local_transcript",
                )
            )
        return cards

    @staticmethod
    def _parse_json_array(raw: str) -> list[dict[str, Any]]:
        """从模型输出中解析 JSON 数组,容忍前后多余文本和代码块标记。"""
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return []
