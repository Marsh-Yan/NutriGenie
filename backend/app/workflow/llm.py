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
    max_tokens: Optional[int] = None,
) -> BaseChatModel:
    """获取 LLM 聊天模型实例

    Args:
        model: 模型名称，默认使用配置中的 LLM_MODEL
        temperature: 温度参数，意图分析用低温度
        timeout: 超时秒数
        max_tokens: 最大输出 token 数；未提供时沿用服务商默认值

    Returns:
        ChatOpenAI 实例（兼容 DeepSeek API）
    """
    options = {}
    # DeepSeek V4 defaults to thinking mode. Its current thinking mode does
    # not accept forced tool_choice or JSON response_format, both of which are
    # used by this workflow for deterministic parsing. Disable thinking for
    # these structured application calls as documented by DeepSeek.
    if "deepseek" in (settings.LLM_API_BASE or "").lower():
        options["extra_body"] = {"thinking": {"type": "disabled"}}

    if max_tokens is not None:
        options["max_tokens"] = max_tokens

    return ChatOpenAI(
        model=model or settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_API_BASE,
        temperature=temperature,
        timeout=timeout or settings.LLM_TIMEOUT,
        **options,
    )
