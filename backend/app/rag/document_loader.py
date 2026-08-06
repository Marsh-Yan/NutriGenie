"""Markdown 知识库加载器。

菜谱的结构化事实仍保留在 MySQL。本模块只读取包含 recipe_id 的增强描述，
用于生成可追溯、可重建的 Chroma 索引。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from app.rag.models import KnowledgeDocument


def _parse_frontmatter(raw: str, source: Path) -> tuple[dict[str, Any], str]:
    """解析仅包含标量字段的 YAML frontmatter，避免额外运行时依赖。"""
    if not raw.startswith("---\n"):
        raise ValueError(f"知识文档缺少 frontmatter: {source}")

    marker = raw.find("\n---", 4)
    if marker == -1:
        raise ValueError(f"知识文档 frontmatter 未闭合: {source}")

    frontmatter = raw[4:marker]
    content = raw[marker + 4:].lstrip("\r\n")
    metadata: dict[str, Any] = {}

    for line in frontmatter.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"无效 frontmatter 字段 {source}: {line}")
        key, value = (part.strip() for part in line.split(":", 1))
        if value.isdigit():
            metadata[key] = int(value)
        else:
            metadata[key] = value.strip('"\'')

    return metadata, content


def load_recipe_documents(recipes_dir: str | Path) -> list[KnowledgeDocument]:
    """加载 recipes 目录中的 Markdown 文档。"""
    root = Path(recipes_dir)
    if not root.exists():
        return []

    documents: list[KnowledgeDocument] = []
    for path in sorted(root.glob("*.md")):
        metadata, content = _parse_frontmatter(path.read_text(encoding="utf-8"), path)
        recipe_id = metadata.get("recipe_id")
        if not isinstance(recipe_id, int):
            raise ValueError(f"知识文档缺少整数 recipe_id: {path}")
        if not content.strip():
            raise ValueError(f"知识文档正文为空: {path}")

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        metadata = {
            **metadata,
            "source_file": path.name,
            "content_hash": content_hash,
            "document_type": "recipe_context",
        }
        documents.append(
            KnowledgeDocument(
                document_id=f"recipe-{recipe_id}",
                content=content,
                metadata=metadata,
            )
        )
    return documents
