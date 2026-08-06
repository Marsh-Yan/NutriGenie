"""Markdown、TXT、PDF 的统一解析入口。"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from app.rag.parsing.models import ParsedBlock


def _base_metadata(path: Path, source_type: str) -> dict[str, Any]:
    return {
        "source_file": path.name,
        "source_type": source_type,
        "content_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _fallback_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """仅用于最小环境的标量 frontmatter 解析；生产环境使用 python-frontmatter。"""
    if not raw.startswith("---"):
        return {}, raw
    lines = raw.replace("\r\n", "\n").split("\n")
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, raw
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        return {}, raw
    metadata: dict[str, Any] = {}
    for line in lines[1:end]:
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip("'\"")
        metadata[key.strip()] = int(value) if value.isdigit() else value
    return metadata, "\n".join(lines[end + 1:]).lstrip("\n")


def load_markdown(path: str | Path) -> list[ParsedBlock]:
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    metadata: dict[str, Any] = {}
    content = raw
    try:
        import frontmatter

        post = frontmatter.loads(raw)
        metadata = dict(post.metadata)
        content = post.content
    except ImportError:
        # 兼容仅安装基础依赖的环境；菜谱加载器仍提供严格 frontmatter 校验。
        metadata, content = _fallback_frontmatter(raw)
    base = {**metadata, **_base_metadata(path, "markdown")}
    try:
        from langchain_text_splitters import MarkdownHeaderTextSplitter

        sections = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
            strip_headers=False,
        ).split_text(content)
        return [
            ParsedBlock(content=section.page_content, metadata={**base, **section.metadata})
            for section in sections
            if section.page_content.strip()
        ]
    except ImportError:
        return [ParsedBlock(content=content, metadata=base)]


def load_text(path: str | Path) -> list[ParsedBlock]:
    path = Path(path)
    try:
        from charset_normalizer import from_path

        match = from_path(path).best()
        content = str(match) if match else path.read_text(encoding="utf-8")
    except ImportError:
        content = path.read_text(encoding="utf-8")
    return [ParsedBlock(content=content, metadata=_base_metadata(path, "txt"))]


def load_pdf(path: str | Path) -> list[ParsedBlock]:
    path = Path(path)
    try:
        import pymupdf4llm
    except ImportError as exc:
        raise RuntimeError("PDF 解析需要安装 pymupdf4llm") from exc

    blocks: list[ParsedBlock] = []
    base = _base_metadata(path, "pdf")
    for page in pymupdf4llm.to_markdown(str(path), page_chunks=True):
        text = str(page.get("text", "")).strip()
        if not text:
            continue
        page_metadata = page.get("metadata") or {}
        blocks.append(
            ParsedBlock(
                content=text,
                metadata={
                    **base,
                    "page_number": page_metadata.get("page_number"),
                    "toc_items": page.get("toc_items", []),
                },
            )
        )
    if not blocks:
        raise ValueError("PDF 未提取到文本；请先在系统外完成 OCR，并上传带文本层的 PDF、Markdown 或 TXT")
    return blocks


def load_file(path: str | Path) -> list[ParsedBlock]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return load_markdown(path)
    if suffix in {".txt", ".text"}:
        return load_text(path)
    if suffix == ".pdf":
        return load_pdf(path)
    raise ValueError(f"暂不支持的知识库文件格式: {suffix or '<none>'}")
