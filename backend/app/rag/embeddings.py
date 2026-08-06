"""智谱 Embedding-3 适配器。"""

from __future__ import annotations

from typing import Sequence

import httpx

from app.config import settings


class EmbeddingError(RuntimeError):
    """远程 Embedding 请求失败。"""


class ZhipuEmbeddingFunction:
    """实现 Chroma 所需的同步 embedding function 接口。"""

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.EMBEDDING_API_KEY
        self.api_base = (api_base if api_base is not None else settings.EMBEDDING_API_BASE).rstrip("/")
        self.model = model if model is not None else settings.EMBEDDING_MODEL
        self.dimensions = dimensions if dimensions is not None else settings.EMBEDDING_DIMENSIONS
        self.timeout = timeout

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        return self.embed_documents(list(input))

    @staticmethod
    def name() -> str:
        """Chroma 用于持久化配置比对的稳定名称。"""
        return "nutrigenie_zhipu_embedding"

    @staticmethod
    def build_from_config(config: dict) -> "ZhipuEmbeddingFunction":
        """从 Chroma 持久化配置恢复非敏感连接参数。"""
        return ZhipuEmbeddingFunction(
            api_base=config.get("api_base"),
            model=config.get("model"),
            dimensions=config.get("dimensions"),
        )

    def get_config(self) -> dict:
        """密钥始终从环境变量读取，绝不写入 Chroma 配置。"""
        return {
            "api_base": self.api_base,
            "model": self.model,
            "dimensions": self.dimensions,
        }

    def is_legacy(self) -> bool:
        return False

    def embed_query(self, input: str | Sequence[str]) -> list[float] | list[list[float]]:
        """兼容应用侧单条查询与 Chroma 传入的批量查询。"""
        if isinstance(input, str):
            return self.embed_documents([input])[0]
        return self.embed_documents(list(input))

    def default_space(self) -> str:
        return "cosine"

    def supported_spaces(self) -> list[str]:
        return ["cosine", "l2", "ip"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.api_key:
            raise EmbeddingError("未配置 EMBEDDING_API_KEY，无法调用智谱 Embedding API")

        payload = {
            "model": self.model,
            "input": texts,
            "dimensions": self.dimensions,
        }
        try:
            response = httpx.post(
                f"{self.api_base}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            ordered = sorted(data, key=lambda item: item["index"])
            embeddings = [item["embedding"] for item in ordered]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise EmbeddingError(f"智谱 Embedding 调用失败: {exc}") from exc

        if len(embeddings) != len(texts):
            raise EmbeddingError("智谱 Embedding 返回数量与请求数量不一致")
        return embeddings
