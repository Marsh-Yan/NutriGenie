"""通用知识库文档和索引状态模型。"""

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint, func

from app.db.database import Base


class KnowledgeDocumentRecord(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (UniqueConstraint("source_file", name="uq_knowledge_source_file"),)

    document_id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="pending", index=True)
    indexed_chunks = Column(Integer, nullable=False, default=0)
    embedding_provider = Column(String(50), nullable=True)
    embedding_model = Column(String(100), nullable=True)
    embedding_dimensions = Column(Integer, nullable=True)
    embedding_version = Column(String(180), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class KnowledgeChunkRecord(Base):
    __tablename__ = "knowledge_chunks"

    chunk_id = Column(String(255), primary_key=True)
    document_id = Column(Integer, nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    token_count = Column(Integer, nullable=True)
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class KnowledgeIngestionJob(Base):
    __tablename__ = "knowledge_ingestion_jobs"

    job_id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="queued", index=True)
    stage = Column(String(30), nullable=False, default="queued")
    indexed_chunks = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
