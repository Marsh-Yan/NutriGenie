"""通用知识文档的解析、增量索引和状态更新。"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import SessionLocal
from app.models.knowledge import KnowledgeChunkRecord, KnowledgeDocumentRecord, KnowledgeIngestionJob
from app.rag.parsing.pipeline import ingest_file
from app.rag.vector_store import KnowledgeVectorStore
from app.services.knowledge_storage import LocalKnowledgeStorage

logger = logging.getLogger(__name__)


def index_document(
    db: Session,
    record: KnowledgeDocumentRecord,
    source_path: str | Path,
    *,
    vector_store: KnowledgeVectorStore | None = None,
) -> int:
    """索引一个文档；失败时记录状态而不是留下 processing。"""
    record.status = "processing"
    record.error_message = None
    record.embedding_provider = settings.EMBEDDING_PROVIDER
    record.embedding_model = settings.EMBEDDING_MODEL
    record.embedding_dimensions = settings.EMBEDDING_DIMENSIONS
    record.embedding_version = (
        f"{settings.EMBEDDING_PROVIDER}:{settings.EMBEDDING_MODEL}:{settings.EMBEDDING_DIMENSIONS}"
    )
    db.commit()
    try:
        chunks = ingest_file(source_path, document_id=str(record.document_id), version=record.version)
        store = vector_store or KnowledgeVectorStore()
        store.upsert(chunks)
        old = db.query(KnowledgeChunkRecord).filter_by(document_id=record.document_id).all()
        current_ids = {chunk.chunk_id for chunk in chunks}
        stale_ids = [chunk.chunk_id for chunk in old if chunk.chunk_id not in current_ids]
        if stale_ids:
            store.collection.delete(ids=stale_ids)
            for chunk in old:
                if chunk.chunk_id in stale_ids:
                    db.delete(chunk)
        for chunk in chunks:
            db.merge(
                KnowledgeChunkRecord(
                    chunk_id=chunk.chunk_id,
                    document_id=record.document_id,
                    chunk_index=int(chunk.metadata["chunk_index"]),
                    content_hash=str(chunk.metadata.get("content_hash", "")),
                    page_number=chunk.metadata.get("page_number"),
                    section_title=chunk.metadata.get("h2") or chunk.metadata.get("h1"),
                )
            )
        record.indexed_chunks = len(chunks)
        record.status = "ready"
        db.commit()
        return len(chunks)
    except Exception as exc:
        db.rollback()
        record = db.get(KnowledgeDocumentRecord, record.document_id)
        if record:
            record.status = "failed"
            record.error_message = str(exc)[:2000]
            db.commit()
        raise


def run_index_job(document_id: int, source_dir: str | Path, job_id: int | None = None) -> None:
    """后台任务入口：自行创建和关闭数据库会话，避免复用请求会话。"""
    db = SessionLocal()
    try:
        record = db.get(KnowledgeDocumentRecord, document_id)
        if not record:
            return
        job = db.get(KnowledgeIngestionJob, job_id) if job_id else None
        if job:
            job.retry_count += 1
            job.status = "running"
            job.stage = "parsing"
            job.started_at = datetime.now(timezone.utc)
            db.commit()
        source_path = Path(source_dir) / record.source_file
        if not source_path.exists():
            record.status = "failed"
            record.error_message = "Source file is missing"
            if job:
                job.status = "failed"
                job.stage = "source_check"
                job.error_message = record.error_message
                job.finished_at = datetime.now(timezone.utc)
            db.commit()
            return
        if job:
            job.stage = "embedding"
            db.commit()
        count = index_document(db, record, source_path)
        if job:
            job.status = "succeeded"
            job.stage = "completed"
            job.indexed_chunks = count
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as exc:
        # index_document 已记录可展示的失败原因；后台任务不能再向客户端抛异常。
        db.rollback()
        job = db.get(KnowledgeIngestionJob, job_id) if job_id else None
        if job:
            job.status = "failed"
            job.stage = "error"
            job.error_message = str(exc)[:2000]
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        logger.exception("Knowledge ingestion job failed: document_id=%s job_id=%s", document_id, job_id)
    finally:
        db.close()


def delete_document(
    db: Session,
    record: KnowledgeDocumentRecord,
    source_dir: str | Path,
    *,
    vector_store: KnowledgeVectorStore | None = None,
    storage: LocalKnowledgeStorage | None = None,
) -> None:
    """删除文档的向量、chunk、任务记录和源文件。"""
    source_root = Path(source_dir).resolve()
    source_path = (source_root / record.source_file).resolve()
    if source_path.parent != source_root:
        raise ValueError("知识库源文件路径非法")

    store = vector_store or KnowledgeVectorStore()
    store.delete_document(record.document_id)
    if storage:
        storage.delete(record.source_file)
    elif source_path.exists():
        source_path.unlink()
    db.query(KnowledgeChunkRecord).filter_by(document_id=record.document_id).delete()
    db.query(KnowledgeIngestionJob).filter_by(document_id=record.document_id).delete()
    db.delete(record)
    db.commit()
