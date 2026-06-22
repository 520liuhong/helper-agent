"""
LLM 工厂
基于 LangChain ChatOpenAI 创建 DeepSeek / Qwen 模型实例
"""
import os

from langchain_openai import ChatOpenAI

from config import config


def _ensure_v1_base_url(base_url: str) -> str:
    """确保 OpenAI 兼容接口 base_url 以 /v1 结尾"""
    url = base_url.rstrip("/")
    if not url.endswith("/v1"):
        url = f"{url}/v1"
    return url


def create_llm(
    model: str,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    streaming: bool = False,
    use_vl: bool = False,
) -> ChatOpenAI:
    """
    根据模型名称创建 LangChain ChatOpenAI 实例

    Args:
        model: "deepseek" 或 "qwen"
        temperature: 采样温度
        max_tokens: 最大输出 token 数
        streaming: 是否启用流式输出
    """
    kwargs: dict = {
        "temperature": temperature,
        "streaming": streaming,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    if model == "deepseek":
        api_key = config.deepseek.api_key or os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY 未配置")
        return ChatOpenAI(
            model=config.deepseek.model,
            api_key=api_key,
            base_url=_ensure_v1_base_url(config.deepseek.base_url),
            **kwargs,
        )

    if model == "qwen":
        api_key = config.qwen.api_key or os.getenv("QWEN_API_KEY", "")
        if not api_key:
            raise ValueError("QWEN_API_KEY 未配置")
        return ChatOpenAI(
            model=config.qwen.vl_model if use_vl else config.qwen.model,
            api_key=api_key,
            base_url=_ensure_v1_base_url(config.qwen.base_url),
            **kwargs,
        )

    raise ValueError(f"不支持的模型: {model}，支持的模型: deepseek, qwen")
