"""解析阶段的统一数据模型。"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParsedBlock:
    """一个来自原始文件的可追踪文本块。"""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeChunk:
    """可直接发送给 Embedding 和向量数据库的最终块。"""

    chunk_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
