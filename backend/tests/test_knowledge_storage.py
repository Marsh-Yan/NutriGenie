from pathlib import Path

import pytest

from app.services.knowledge_storage import LocalKnowledgeStorage


def test_local_storage_saves_and_deletes_files(tmp_path: Path):
    storage = LocalKnowledgeStorage(tmp_path)

    saved = storage.save("guide.md", b"hello")

    assert saved.read_bytes() == b"hello"
    assert storage.exists("guide.md")
    storage.delete("guide.md")
    assert not storage.exists("guide.md")


def test_local_storage_canonicalizes_path_traversal_input(tmp_path: Path):
    storage = LocalKnowledgeStorage(tmp_path)

    # Path.name canonicalizes user-provided filenames to a single basename.
    assert storage.path("nested/guide.md").parent == tmp_path.resolve()
