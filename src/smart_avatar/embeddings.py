from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol

from .config import EmbeddingConfig


class EmbeddingClient(Protocol):
    """文本向量化抽象。遵循设计文档 5.2:使用本地嵌入模型将事件和洞察字段转为向量。"""

    provider_name: str
    dimension: int

    def embed(self, text: str) -> list[float]:
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...


@dataclass(frozen=True)
class DryRunEmbeddingClient:
    """占位嵌入器。未配置真实模型时使用确定性哈希生成伪向量。

    保证向量检索框架可跑通,且相同文本始终得到相同向量,
    语义相近的中文文本因共享字符也有一定相似度。
    """

    provider_name: str = "dry_run"
    dimension: int = 256

    def embed(self, text: str) -> list[float]:
        return self._hash_vector(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_vector(text) for text in texts]

    def _hash_vector(self, text: str) -> list[float]:
        """用 SHA256 滚动哈希生成确定性向量,叠加字符频率特征。"""
        vec = [0.0] * self.dimension
        if not text:
            return vec
        # 字符级特征:每个字符映射到向量维度
        for char in text:
            if char.isspace():
                continue
            idx = ord(char) % self.dimension
            vec[idx] += 1.0
        # 哈希特征:用 n-gram 哈希补充局部顺序信息
        normalized = text.lower().strip()
        for n in (1, 2, 3):
            for i in range(max(0, len(normalized) - n + 1)):
                gram = normalized[i : i + n]
                digest = hashlib.sha256(gram.encode("utf-8")).digest()
                idx = int.from_bytes(digest[:4], "little") % self.dimension
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vec[idx] += sign * 0.5
        # L2 归一化
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


@dataclass
class LocalEmbeddingClient:
    """基于 sentence-transformers 的本地嵌入器。

    使用 bge-large-zh-v1.5 中文嵌入模型,完全离线运行。
    模型实例全局缓存,避免每次推理重新加载。
    """

    model_name: str = "BAAI/bge-large-zh-v1.5"
    provider_name: str = "local"
    dimension: int = 1024
    _model: object = None

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers 未安装。请执行 pip install -e .[embedding] 安装嵌入依赖。"
                ) from exc
            # 国内网络兜底:HuggingFace 镜像(可被环境变量覆盖)
            import os  # noqa: PLC0415
            os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        model = self._get_model()
        vec = model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        vecs = model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]


def create_embedding_client(config: EmbeddingConfig) -> EmbeddingClient:
    """根据配置创建嵌入器。provider 可选:dry_run / local。"""
    if config.provider == "local":
        return LocalEmbeddingClient(
            model_name=config.model_name,
            dimension=config.dimension,
        )
    return DryRunEmbeddingClient(dimension=config.dimension)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算余弦相似度。向量已归一化时等价于点积。"""
    min_len = min(len(a), len(b))
    if min_len == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(min_len))
    norm_a = math.sqrt(sum(x * x for x in a[:min_len]))
    norm_b = math.sqrt(sum(x * x for x in b[:min_len]))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
