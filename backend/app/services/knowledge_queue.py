"""索引任务队列适配器：本地 BackgroundTasks 或可选 Redis/RQ。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import settings
from app.services.knowledge_index import run_index_job


def enqueue_index_job(background_tasks: Any, document_id: int, source_dir: str | Path, job_id: int) -> str:
    """将索引任务放入配置的队列，返回 backend 名称。"""
    if settings.KNOWLEDGE_QUEUE_BACKEND == "rq":
        try:
            from redis import Redis
            from rq import Queue, Retry
        except ImportError as exc:
            raise RuntimeError("RQ 队列需要安装 rq 和 redis 依赖") from exc
        queue = Queue("nutrigenie-knowledge", connection=Redis.from_url(settings.KNOWLEDGE_REDIS_URL))
        job = queue.enqueue(
            run_index_job,
            document_id,
            str(source_dir),
            job_id,
            job_timeout="10m",
            retry=Retry(
                max=settings.KNOWLEDGE_MAX_RETRIES,
                interval=settings.KNOWLEDGE_RETRY_BACKOFF_SECONDS,
            ),
        )
        job.meta.update({"document_id": document_id, "ingestion_job_id": job_id})
        job.save_meta()
        return "rq"
    background_tasks.add_task(
        run_index_job,
        document_id,
        str(source_dir),
        job_id,
    )
    return "background"
