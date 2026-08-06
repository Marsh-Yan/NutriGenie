"""LLM 客户端封装

基于 langchain-openai，兼容 DeepSeek、OpenAI 等 API。
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm(
    model: Optional[str] = None,
    temperature: float = 0.1,
    timeout: Optional[int] = None,
) -> BaseChatModel:
    """获取 LLM 聊天模型实例

    Args:
        model: 模型名称，默认使用配置中的 LLM_MODEL
        temperature: 温度参数，意图分析用低温度
        timeout: 超时秒数

    Returns:
        ChatOpenAI 实例（兼容 DeepSeek API）
    """
    return ChatOpenAI(
        model=model or settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_API_BASE,
        temperature=temperature,
        timeout=timeout or settings.LLM_TIMEOUT,
    )
