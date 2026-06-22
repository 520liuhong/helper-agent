"""
DeepSeek API服务
封装与DeepSeek API的交互（OpenAI兼容接口）
"""
import os
from typing import Iterator, Optional

from openai import OpenAI

from config import config


class DeepSeekService:
    """DeepSeek API服务类"""

    def __init__(self):
        self._api_key = config.deepseek.api_key or os.getenv("DEEPSEEK_API_KEY")
        self._base_url = config.deepseek.base_url
        self.model = config.deepseek.model
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self._api_key:
                raise ValueError("DEEPSEEK_API_KEY 未配置")
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    def chat(
        self,
        messages: list[dict],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> dict | Iterator[dict]:
        """
        发送对话请求到DeepSeek API

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            stream: 是否使用流式响应
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            流式响应时返回Iterator，非流式时返回dict
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        if stream:
            return self._stream_chat(**kwargs)

        response = self.client.chat.completions.create(stream=False, **kwargs)
        return self._format_response(response)

    def _format_response(self, response) -> dict:
        """格式化响应"""
        choice = response.choices[0]
        usage = response.usage
        return {
            "id": response.id,
            "model": response.model,
            "choices": [
                {
                    "index": choice.index,
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content,
                    },
                    "finish_reason": choice.finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
        }

    def _stream_chat(self, **kwargs) -> Iterator[dict]:
        """流式响应处理"""
        response = self.client.chat.completions.create(stream=True, **kwargs)
        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = delta.content or ""
            if content:
                yield {
                    "id": chunk.id,
                    "choices": [
                        {
                            "index": chunk.choices[0].index,
                            "delta": {"content": content},
                            "finish_reason": chunk.choices[0].finish_reason,
                        }
                    ],
                }


# 全局服务实例
deepseek_service = DeepSeekService()
