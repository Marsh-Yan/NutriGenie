"""通用文件 ingestion 管线：解析、切分、生成稳定 chunk ID。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.rag.parsing.chunker import split_blocks
from app.rag.parsing.loaders import load_file
from app.rag.parsing.models import KnowledgeChunk


def _vector_metadata(metadata: dict) -> dict:
    """Chroma metadata 只接受标量；复杂 frontmatter 转为 JSON 字符串。"""
    result = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = value
        else:
            result[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return result


def ingest_file(
    path: str | Path,
    *,
    document_id: str | None = None,
    version: int = 1,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[KnowledgeChunk]:
    """把 Markdown/TXT/PDF 转为稳定 ID 的可索引 chunks。"""
    source = Path(path)
    doc_id = document_id or hashlib.sha256(str(source.resolve()).encode()).hexdigest()[:16]
    blocks = split_blocks(
        load_file(source),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks: list[KnowledgeChunk] = []
    for index, block in enumerate(blocks):
        chunk_id = f"document-{doc_id}-v{version}-chunk-{index}"
        chunks.append(
            KnowledgeChunk(
                chunk_id=chunk_id,
                content=block.content,
                metadata={
                    **_vector_metadata(block.metadata),
                    "document_id": doc_id,
                    "document_version": version,
                    "chunk_index": index,
                },
            )
        )
    return chunks
