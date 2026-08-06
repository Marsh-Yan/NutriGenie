from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.knowledge import KnowledgeChunkRecord, KnowledgeDocumentRecord, KnowledgeIngestionJob
from app.services.knowledge_index import delete_document


class FakeVectorStore:
    def __init__(self):
        self.deleted = []

    def delete_document(self, document_id):
        self.deleted.append(document_id)


def test_delete_document_removes_file_chunks_jobs_and_vectors(tmp_path: Path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        KnowledgeDocumentRecord.__table__,
        KnowledgeChunkRecord.__table__,
        KnowledgeIngestionJob.__table__,
    ])
    session = sessionmaker(bind=engine)()
    source = tmp_path / "guide.md"
    source.write_text("knowledge", encoding="utf-8")
    record = KnowledgeDocumentRecord(
        source_file=source.name,
        file_type="md",
        content_hash="a" * 64,
        status="ready",
    )
    session.add(record)
    session.flush()
    session.add(KnowledgeChunkRecord(
        chunk_id="document-1-v1-chunk-0", document_id=record.document_id,
        chunk_index=0, content_hash="b" * 64,
    ))
    session.add(KnowledgeIngestionJob(document_id=record.document_id, status="succeeded", stage="completed"))
    session.commit()
    document_id = record.document_id
    fake_store = FakeVectorStore()

    delete_document(session, record, tmp_path, vector_store=fake_store)

    assert fake_store.deleted == [document_id]
    assert not source.exists()
    assert session.query(KnowledgeDocumentRecord).count() == 0
    assert session.query(KnowledgeChunkRecord).count() == 0
    assert session.query(KnowledgeIngestionJob).count() == 0
