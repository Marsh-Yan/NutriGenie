"""RAG 模块使用的轻量数据模型。"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class KnowledgeDocument:
    """可写入向量库的一篇知识文档。"""

    document_id: str
    content: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RetrievedRecipe:
    """语义检索命中的菜谱及标准化相似度。"""

    recipe_id: int
    content: str
    metadata: dict[str, Any]
    similarity_score: float


@dataclass(frozen=True)
class RetrievedChunk:
    """通用知识库检索结果，携带可展示的来源信息。"""

    chunk_id: str
    content: str
    metadata: dict[str, Any]
    similarity_score: float
