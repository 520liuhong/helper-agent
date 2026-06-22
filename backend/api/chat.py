"""
聊天API路由
通过 LangChain Agent 处理对话，支持流式和非流式响应

API 端点：
- POST /api/chat - 核心聊天接口
- GET /api/models - 获取支持的模型列表
- GET /api/tools - 获取 Agent 可用工具列表

响应格式：
- 非流式：OpenAI 兼容格式
- 流式：Server-Sent Events (SSE) 格式
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Literal, AsyncIterator
import inspect
import json

from agents.agent_service import agent_service  # Agent 核心服务

router = APIRouter()


class Attachment(BaseModel):
    """
    消息附件模型
    
    支持图片和文件附件，用于多模态对话场景。
    """
    url: str = Field(..., description="文件URL（本地路径或远程URL）")
    filename: str = Field(..., description="原始文件名")
    type: str = Field("image", description="附件类型: image/file")


class Message(BaseModel):
    """
    消息模型
    
    遵循 OpenAI Chat API 格式，支持角色和附件。
    """
    role: str = Field(..., description="角色: user/assistant/system")
    content: str = Field(..., description="消息内容")
    attachments: list[Attachment] = Field(default_factory=list, description="附件列表（图片等）")


class ChatRequest(BaseModel):
    """
    聊天请求模型
    
    请求参数说明：
    - messages: 消息历史列表
    - model: 选择使用的AI模型（deepseek/qwen）
    - stream: 是否启用流式响应
    - temperature: 温度参数（0-2，越高越随机）
    - max_tokens: 最大输出token数（可选）
    """
    messages: list[Message] = Field(..., description="消息列表")
    model: Literal["deepseek", "qwen"] = Field("deepseek", description="AI模型")
    stream: bool = Field(False, description="是否流式响应")
    temperature: float = Field(0.7, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(None, description="最大token数")


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    聊天接口
    通过 LangChain Agent 处理，支持工具调用、流式和非流式响应
    """
    try:
        messages = [
            {
                "role": msg.role,
                "content": msg.content,
                **({"attachments": [a.model_dump() for a in msg.attachments]} if msg.attachments else {}),
            }
            for msg in request.messages
        ]

        if request.stream:
            return StreamingResponse(
                stream_chat(messages, request.model, request.temperature, request.max_tokens),
                media_type="text/event-stream",
            )

        response = agent_service.chat(
            messages=messages,
            model=request.model,
            stream=False,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 处理失败: {str(e)}")


async def _iter_agent_chunks(
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: Optional[int],
):
    """统一迭代 Agent 流式输出"""
    stream = agent_service.chat(
        messages=messages,
        model=model,
        stream=True,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if inspect.iscoroutine(stream):
        raise TypeError("agent_service.chat(stream=True) 返回了协程对象")

    if inspect.isasyncgen(stream):
        async for chunk in stream:
            yield chunk
        return

    for chunk in stream:
        yield chunk


async def stream_chat(
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: Optional[int],
) -> AsyncIterator[str]:
    """流式响应生成器"""
    try:
        async for chunk in _iter_agent_chunks(messages, model, temperature, max_tokens):
            if chunk["choices"][0]["delta"].get("content"):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"


@router.get("/models")
async def list_models():
    """获取支持的模型列表"""
    return {
        "models": [
            {
                "id": "deepseek",
                "name": "DeepSeek",
                "description": "深度求索 AI Agent（LangChain + 工具调用）",
            },
            {
                "id": "qwen",
                "name": "Qwen",
                "description": "通义千问 AI Agent（LangChain + 工具调用）",
            },
        ]
    }


@router.get("/tools")
async def list_tools():
    """获取 Agent 可用工具列表"""
    from agents.tools import get_agent_tools

    tools = get_agent_tools()
    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in tools
        ]
    }
