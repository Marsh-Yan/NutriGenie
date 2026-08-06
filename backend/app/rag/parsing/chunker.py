"""面向中文和 Markdown 的结构化文本切分。"""

from __future__ import annotations

from typing import Any

from app.rag.parsing.models import ParsedBlock


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """轻量递归切分器，避免在未安装 LangChain 时阻塞基础解析测试。"""
    if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_size 必须大于 0，chunk_overlap 必须小于 chunk_size")
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            window = text[start:end]
            boundary = -1
            for separator in separators:
                candidate = window.rfind(separator)
                if candidate > max(0, len(window) // 2):
                    boundary = candidate + len(separator)
                    break
            if boundary > 0:
                end = start + boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(start + 1, end - chunk_overlap)
    return chunks


def split_blocks(
    blocks: list[ParsedBlock],
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    keep_short_blocks: bool = True,
) -> list[ParsedBlock]:
    """将解析块切成最终索引块，并保留页码、标题等元数据。"""
    result: list[ParsedBlock] = []
    for block in blocks:
        pieces = _split_with_langchain(block.content, chunk_size, chunk_overlap)
        for index, piece in enumerate(pieces):
            metadata: dict[str, Any] = {
                **block.metadata,
                "chunk_index": index,
                "chunk_size": len(piece),
            }
            result.append(ParsedBlock(content=piece, metadata=metadata))
    return result


def _split_with_langchain(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """优先使用主流开源 splitter；基础环境缺少依赖时使用等价轻量后备实现。"""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return splitter.split_text(text)
    except ImportError:
        return _split_text(text, chunk_size, chunk_overlap)
