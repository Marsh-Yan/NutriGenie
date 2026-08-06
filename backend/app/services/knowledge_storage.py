"""知识库原始文件存储抽象；当前实现为本地磁盘，接口可替换为 S3/OSS。"""

from __future__ import annotations

from pathlib import Path


class LocalKnowledgeStorage:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, filename: str) -> Path:
        safe_name = Path(filename).name
        target = (self.root / safe_name).resolve()
        if target.parent != self.root:
            raise ValueError("知识库文件路径非法")
        return target

    def save(self, filename: str, content: bytes) -> Path:
        target = self.path(filename)
        target.write_bytes(content)
        return target

    def exists(self, filename: str) -> bool:
        return self.path(filename).exists()

    def delete(self, filename: str) -> None:
        target = self.path(filename)
        if target.exists():
            target.unlink()
