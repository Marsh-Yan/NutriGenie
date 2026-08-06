"""Chroma 持久化向量库封装。"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from app.config import settings
from app.rag.embeddings import ZhipuEmbeddingFunction
from app.rag.models import KnowledgeDocument, RetrievedChunk, RetrievedRecipe
from app.rag.parsing.models import KnowledgeChunk

COLLECTION_NAME = "nutrigenie_recipe_context"
KNOWLEDGE_COLLECTION_NAME = "nutrigenie_knowledge"


def _get_chromadb() -> Any:
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            "未安装 chromadb。请在 backend 虚拟环境执行 pip install -r requirements.txt"
        ) from exc
    return chromadb


class RecipeVectorStore:
    """菜谱增强描述的可重建 Chroma 索引。"""

    def __init__(self, persist_dir: str | Path | None = None, embedding_function: Any = None) -> None:
        chromadb = _get_chromadb()
        self.persist_dir = Path(persist_dir or settings.CHROMA_PERSIST_DIR)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.embedding_function = embedding_function or ZhipuEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    def rebuild(self, documents: list[KnowledgeDocument]) -> int:
        """删除旧索引并全量写入当前知识库。"""
        try:
            self.client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )
        if not documents:
            return 0
        self.collection.add(
            ids=[doc.document_id for doc in documents],
            documents=[doc.content for doc in documents],
            metadatas=[doc.metadata for doc in documents],
        )
        return len(documents)

    def upsert_chunks(self, chunks: list[KnowledgeChunk]) -> int:
        """增量写入通用知识块；稳定 ID 使重复索引不会产生重复向量。"""
        if not chunks:
            return 0
        self.collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.content for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
        )
        return len(chunks)

    def delete_chunks(self, chunk_ids: list[str]) -> int:
        """按稳定 chunk ID 删除已移除或过期的知识。"""
        if not chunk_ids:
            return 0
        self.collection.delete(ids=chunk_ids)
        return len(chunk_ids)

    def search(self, query: str, limit: int | None = None) -> list[RetrievedRecipe]:
        """按余弦距离搜索并将结果标准化为 0~1 相似度。"""
        if self.collection.count() == 0:
            return []
        result = self.collection.query(
            query_texts=[query],
            n_results=min(limit or settings.RAG_RETRIEVAL_TOP_K, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        retrieved: list[RetrievedRecipe] = []
        for content, metadata, distance in zip(documents, metadatas, distances):
            recipe_id = int(metadata["recipe_id"])
            retrieved.append(
                RetrievedRecipe(
                    recipe_id=recipe_id,
                    content=content,
                    metadata=metadata,
                    similarity_score=max(0.0, min(1.0, 1.0 - float(distance))),
                )
            )
        return retrieved

    def search_by_embeddings(
        self,
        query_embeddings: list[list[float]],
        limit: int | None = None,
    ) -> list[list[RetrievedRecipe]]:
        """批量查询已生成的向量，适用于离线评测以减少远程 Embedding 调用。"""
        if self.collection.count() == 0:
            return [[] for _ in query_embeddings]
        result = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=min(limit or settings.RAG_RETRIEVAL_TOP_K, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        batches: list[list[RetrievedRecipe]] = []
        for documents, metadatas, distances in zip(
            result.get("documents", []), result.get("metadatas", []), result.get("distances", []),
        ):
            batches.append([
                RetrievedRecipe(
                    recipe_id=int(metadata["recipe_id"]),
                    content=content,
                    metadata=metadata,
                    similarity_score=max(0.0, min(1.0, 1.0 - float(distance))),
                )
                for content, metadata, distance in zip(documents, metadatas, distances)
            ])
        return batches


class KnowledgeVectorStore:
    """通用知识块向量库，和菜谱兼容 collection 分开。"""

    def __init__(self, persist_dir: str | Path | None = None, embedding_function: Any = None) -> None:
        chromadb = _get_chromadb()
        self.persist_dir = Path(persist_dir or settings.CHROMA_PERSIST_DIR)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.embedding_function = embedding_function or ZhipuEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=KNOWLEDGE_COLLECTION_NAME,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, chunks: list[KnowledgeChunk]) -> int:
        if not chunks:
            return 0
        self.collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.content for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
        )
        return len(chunks)

    def delete_document(self, document_id: int | str) -> None:
        self.collection.delete(where={"document_id": str(document_id)})

    def search(
        self,
        query: str,
        limit: int = 8,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """向量检索并保留 chunk/source 元数据。"""
        if not query.strip() or self.collection.count() == 0:
            return []
        result = self.collection.query(
            query_texts=[query],
            n_results=min(max(1, limit), self.collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [
            RetrievedChunk(
                chunk_id=chunk_id,
                content=content,
                metadata=metadata or {},
                similarity_score=max(0.0, min(1.0, 1.0 - float(distance))),
            )
            for chunk_id, content, metadata, distance in zip(ids, documents, metadatas, distances)
        ]

    @staticmethod
    def _terms(text: str) -> set[str]:
        """轻量中英文分词：中文使用二元词，英文/数字按词切分。"""
        terms: set[str] = set()
        for token in re.findall(r"[\u4e00-\u9fff]+|[A-Za-z0-9_]+", text.lower()):
            if all("\u4e00" <= char <= "\u9fff" for char in token):
                terms.update(token[index:index + 2] for index in range(max(1, len(token) - 1)))
            else:
                terms.add(token)
        return terms

    def hybrid_search(
        self,
        query: str,
        limit: int = 8,
        where: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """合并向量相似度和关键词重合度，不引入 Reranker。"""
        if not query.strip() or self.collection.count() == 0:
            return []
        vector_results = self.search(query, limit=self.collection.count(), where=where)
        query_terms = self._terms(query)
        scored: list[RetrievedChunk] = []
        for item in vector_results:
            doc_terms = self._terms(item.content)
            keyword_score = len(query_terms & doc_terms) / max(1, len(query_terms))
            combined = (
                settings.RAG_VECTOR_WEIGHT * item.similarity_score
                + settings.RAG_KEYWORD_WEIGHT * keyword_score
            )
            if combined >= settings.RAG_MIN_SIMILARITY:
                scored.append(
                    RetrievedChunk(
                        chunk_id=item.chunk_id,
                        content=item.content,
                        metadata={**item.metadata, "keyword_score": round(keyword_score, 6)},
                        similarity_score=max(0.0, min(1.0, combined)),
                    )
                )
        unique: dict[str, RetrievedChunk] = {}
        for item in sorted(scored, key=lambda result: result.similarity_score, reverse=True):
            content_hash = str(item.metadata.get("content_hash") or item.content)
            unique.setdefault(content_hash, item)
        return list(unique.values())[:limit]
