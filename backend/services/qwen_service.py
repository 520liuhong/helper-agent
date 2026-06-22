"""
Qwen API服务
封装与Qwen(通义千问) API的交互，支持文本与视觉多模态
"""
import os
from typing import Iterator, Optional
import dashscope
from dashscope import Generation, MultiModalConversation

from config import config
from services.message_utils import build_qwen_messages


class QwenService:
    """Qwen API服务类"""

    def __init__(self):
        dashscope.api_key = config.qwen.api_key or os.getenv("QWEN_API_KEY")
        self.model = config.qwen.model or "qwen-turbo"
        self.vl_model = config.qwen.vl_model or "qwen-vl-plus"

    def chat(
        self,
        messages: list[dict],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> dict | Iterator[dict]:
        """
        发送对话请求到Qwen API

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            stream: 是否使用流式响应
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            流式响应时返回Iterator，非流式时返回dict
        """
        transformed, has_images = build_qwen_messages(messages)

        if has_images:
            return self._multimodal_chat(
                transformed,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "result_format": "message",
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        if stream:
            return self._stream_text_chat(**kwargs)

        response = Generation.call(**kwargs)
        return self._format_response(response, self.model)

    def _multimodal_chat(
        self,
        messages: list[dict],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> dict | Iterator[dict]:
        """视觉多模态对话"""
        kwargs = {
            "model": self.vl_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        if stream:
            return self._stream_multimodal_chat(**kwargs)

        response = MultiModalConversation.call(**kwargs)
        return self._format_multimodal_response(response)

    def _format_response(self, response, model: str) -> dict:
        """格式化文本模型响应"""
        if response.status_code != 200:
            raise Exception(f"Qwen API错误: {response.message}")

        output = response.output
        usage = output.get("usage", {}) if hasattr(output, "get") else getattr(output, "usage", {}) or {}
        input_tokens = usage.get("input_tokens", 0) if isinstance(usage, dict) else getattr(usage, "input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0) if isinstance(usage, dict) else getattr(usage, "output_tokens", 0)

        return {
            "id": response.request_id,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": output["choices"][0]["message"]["role"],
                        "content": output["choices"][0]["message"]["content"],
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }

    def _extract_multimodal_text(self, content) -> str:
        """从 Qwen 多模态响应 content 中提取文本（可能是 list/dict 结构）"""
        if not content:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            return content.get("text", "") or ""
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text", "")
                    if text:
                        parts.append(text)
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts)
        return str(content)

    def _format_multimodal_response(self, response) -> dict:
        """格式化多模态模型响应"""
        if response.status_code != 200:
            raise Exception(f"Qwen VL API错误: {response.message}")

        output = response.output
        usage = response.usage or {}
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0

        content = ""
        if output.choices:
            message = output.choices[0].message
            raw_content = getattr(message, "content", "") or ""
            content = self._extract_multimodal_text(raw_content)

        return {
            "id": response.request_id,
            "model": self.vl_model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }

    def _stream_text_chat(self, **kwargs) -> Iterator[dict]:
        """文本模型流式响应"""
        responses = Generation.call(
            **kwargs,
            stream=True,
            incremental_output=True,
        )
        for chunk in responses:
            if chunk.status_code != 200:
                continue

            content = ""
            if chunk.output and chunk.output.choices:
                message = chunk.output.choices[0].get("message", {})
                content = message.get("content", "") if isinstance(message, dict) else getattr(message, "content", "")

            if content:
                yield {
                    "id": chunk.request_id,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": content},
                            "finish_reason": None,
                        }
                    ],
                }

    def _stream_multimodal_chat(self, **kwargs) -> Iterator[dict]:
        """多模态模型流式响应"""
        responses = MultiModalConversation.call(
            **kwargs,
            stream=True,
            incremental_output=True,
        )
        for chunk in responses:
            if chunk.status_code != 200:
                continue

            content = ""
            if chunk.output and chunk.output.choices:
                message = chunk.output.choices[0].message
                raw_content = getattr(message, "content", "") or ""
                content = self._extract_multimodal_text(raw_content)

            if content:
                yield {
                    "id": chunk.request_id,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": content},
                            "finish_reason": None,
                        }
                    ],
                }


# 全局服务实例
qwen_service = QwenService()
