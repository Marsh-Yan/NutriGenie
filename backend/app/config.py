"""NutriGenie 应用配置"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    APP_NAME: str = "NutriGenie"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # MySQL 数据库
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "nutrigenie"

    # DeepSeek LLM
    LLM_API_KEY: str = ""
    LLM_API_BASE: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-v4-flash"
    LLM_TIMEOUT: int = 30

    # Authentication. Override JWT_SECRET_KEY in backend/.env outside local demos.
    JWT_SECRET_KEY: str = "nutrigenie-local-development-only-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Local-development registration verification. Do not use this in production.
    DEV_EMAIL_VERIFICATION_CODE: str = "123456"

    # Zhipu Embedding
    EMBEDDING_PROVIDER: str = "zhipu"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_API_BASE: str = "https://open.bigmodel.cn/api/paas/v4"
    EMBEDDING_MODEL: str = "embedding-3"
    EMBEDDING_DIMENSIONS: int = 1024

    # RAG / Chroma
    CHROMA_PERSIST_DIR: str = "data/chroma"
    RAG_RETRIEVAL_TOP_K: int = 30
    RAG_VECTOR_WEIGHT: float = 0.7
    RAG_KEYWORD_WEIGHT: float = 0.3
    RAG_MIN_SIMILARITY: float = 0.15
    KNOWLEDGE_QUEUE_BACKEND: str = "background"
    KNOWLEDGE_REDIS_URL: str = "redis://localhost:6379/0"
    KNOWLEDGE_MAX_RETRIES: int = 3
    KNOWLEDGE_RETRY_BACKOFF_SECONDS: list[int] = [10, 30, 60]
    KNOWLEDGE_MAX_CONCURRENCY: int = 2

    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

settings = Settings()
