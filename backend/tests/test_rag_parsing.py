from pathlib import Path

from app.rag.parsing.chunker import split_blocks
from app.rag.parsing.loaders import load_file, load_markdown, load_text
from app.rag.parsing.pipeline import ingest_file


def test_markdown_loader_keeps_frontmatter_and_headers(tmp_path: Path):
    path = tmp_path / "guide.md"
    path.write_text(
        "---\ntopic: nutrition\n---\n# 总览\n\n建议均衡饮食。\n\n## 早餐\n\n搭配蛋白质。",
        encoding="utf-8",
    )

    blocks = load_markdown(path)

    assert blocks
    assert blocks[0].metadata["topic"] == "nutrition"
    assert blocks[0].metadata["source_type"] == "markdown"
    assert any("早餐" in block.content for block in blocks)


def test_txt_loader_handles_utf8_and_split_overlap(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("第一段。" * 300, encoding="utf-8")

    blocks = split_blocks(load_text(path), chunk_size=100, chunk_overlap=20)

    assert len(blocks) > 1
    assert all(block.metadata["source_type"] == "txt" for block in blocks)
    assert all(block.metadata["chunk_size"] <= 100 for block in blocks)


def test_load_file_rejects_unsupported_format(tmp_path: Path):
    path = tmp_path / "data.csv"
    path.write_text("a,b\n1,2", encoding="utf-8")

    try:
        load_file(path)
    except ValueError as exc:
        assert "不支持" in str(exc)
    else:
        raise AssertionError("unsupported format should fail")


def test_ingest_file_generates_stable_chunk_ids(tmp_path: Path):
    path = tmp_path / "guide.txt"
    path.write_text("饮食建议。" * 30, encoding="utf-8")

    chunks = ingest_file(path, document_id="42", version=3, chunk_size=50, chunk_overlap=10)

    assert chunks
    assert chunks[0].chunk_id.startswith("document-42-v3-chunk-0")
    assert chunks[0].metadata["document_id"] == "42"
    assert chunks[0].metadata["document_version"] == 3
