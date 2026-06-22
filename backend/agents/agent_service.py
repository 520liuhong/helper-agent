"""
LangChain Agent 服务
使用 LangGraph ReAct Agent 处理对话，支持工具调用与流式输出

核心职责：
1. 构建系统提示词（根据可用工具动态生成）
2. 创建 LangGraph ReAct Agent 实例
3. 处理用户对话请求（支持流式/非流式）
4. 处理多模态图片对话（仅 Qwen VL 模型）
5. 格式化响应输出（OpenAI 兼容格式）

工作流程：
┌─────────────────────────────────────────────────────────────┐
│  用户消息 → to_langchain_messages() → LangChain Message    │
│                   │                                         │
│                   ▼                                         │
│  has_images? ─Yes→ 直接调用 Qwen VL 模型                    │
│     │                                                       │
│     No                                                      │
│     ▼                                                       │
│  create_react_agent() → Agent 调用 LLM + Tools            │
│                   │                                         │
│                   ▼                                         │
│  响应格式化 → 返回 OpenAI 兼容格式                          │
└─────────────────────────────────────────────────────────────┘
"""
import uuid
from typing import AsyncIterator, Iterator, Optional

from langchain_core.messages import AIMessage, AIMessageChunk
from langgraph.prebuilt import create_react_agent  # LangGraph ReAct Agent

from agents.llm_factory import create_llm  # LLM 模型工厂
from agents.message_converter import to_langchain_messages  # 消息格式转换
from agents.tools import get_agent_tools  # Agent 工具集
from config import config  # 全局配置


def build_system_prompt() -> str:
    """
    根据已启用的工具动态生成系统提示词
    
    提示词结构：
    1. 角色定义（智能助手 Agent）
    2. 可用工具列表
    3. 使用规则
    
    动态特性：
    - 如果配置了 Tavily API Key，则包含搜索工具说明
    """
    has_search = bool(config.tavily and config.tavily.api_key)

    lines = [
        "你是一个智能助手 Agent，可以使用工具来帮助用户完成任务。",
        "",
        "可用工具：",
        "- calculator: 数学计算",
        "- get_current_datetime: 获取当前时间",
        "- list_uploaded_files: 列出用户上传的文件",
        "- read_uploaded_file: 读取已上传的文本文件",
    ]
    if has_search:
        lines.append("- tavily_search: 联网搜索实时信息（新闻、天气、最新事件等）")

    lines.extend(["", "使用规则："])
    rules = [
        "需要计算时调用 calculator，不要心算",
        "需要当前时间时调用 get_current_datetime",
        "用户询问已上传文件时，先 list_uploaded_files 再按需 read_uploaded_file",
    ]
    if has_search:
        rules.extend([
            "需要最新信息、实时新闻、天气、股价等联网数据时，调用 tavily_search",
            "搜索后整合结果，标注信息来源 URL",
        ])
    rules.extend([
        "用中文回答，简洁清晰",
        "工具返回结果后，整理成用户友好的回复",
    ])
    lines.extend(f"{i}. {rule}" for i, rule in enumerate(rules, 1))
    return "\n".join(lines)


class AgentService:
    """
    LangChain Agent 服务类
    
    封装 LangGraph ReAct Agent 的核心逻辑，提供统一的对话接口。
    
    设计模式：单例模式（全局 agent_service 实例）
    
    核心能力：
    - 支持 DeepSeek/Qwen 双模型
    - 支持流式和非流式响应
    - 支持工具调用（计算器、时间、文件读取、搜索）
    - 支持多模态图片理解（仅 Qwen VL）
    """

    def __init__(self):
        """初始化 Agent 服务"""
        # 加载所有可用工具（计算器、时间、文件操作、搜索等）
        self._tools = get_agent_tools()

    def _create_agent(self, model: str, temperature: float, max_tokens: Optional[int], streaming: bool):
        """
        创建 LangGraph ReAct Agent 实例
        
        Args:
            model: 模型名称 (deepseek/qwen)
            temperature: 采样温度（0-2，越高越随机）
            max_tokens: 最大输出 token 数
            streaming: 是否启用流式输出
        
        Returns:
            LangGraph ReAct Agent 实例
        """
        # 通过工厂方法创建 LLM 实例
        llm = create_llm(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
        )
        
        # 创建 ReAct Agent
        return create_react_agent(
            model=llm,
            tools=self._tools,
            prompt=build_system_prompt(),
        )

    def chat(
        self,
        messages: list[dict],
        model: str = "deepseek",
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> dict | Iterator[dict]:
        """
        核心对话接口 - 通过 LangChain Agent 处理用户请求
        
        Args:
            messages: 消息列表，格式 [{"role": "user/assistant/system", "content": "...", "attachments": [...]}]
            model: 模型名称 (deepseek/qwen)
            stream: 是否流式响应
            temperature: 采样温度（0-2）
            max_tokens: 最大输出 token 数
        
        Returns:
            非流式：完整响应字典（OpenAI 兼容格式）
            流式：响应块迭代器
        """
        # 将 API 消息格式转换为 LangChain Message 格式
        lc_messages, has_images = to_langchain_messages(messages)

        # 特殊处理：含图片时使用 Qwen VL 视觉模型（不启用工具）
        if has_images and model == "qwen":
            return self._vision_chat(lc_messages, stream, temperature, max_tokens)

        # 根据是否流式选择不同处理路径
        if stream:
            return self._stream_agent(model, lc_messages, temperature, max_tokens)

        return self._invoke_agent(model, lc_messages, temperature, max_tokens)

    def _vision_chat(
        self,
        lc_messages: list,
        stream: bool,
        temperature: float,
        max_tokens: Optional[int],
    ) -> dict | Iterator[dict]:
        """
        视觉模型对话 - 处理含图片的消息
        
        注意：视觉模式下不启用工具调用，直接调用 Qwen VL 模型
        
        Args:
            lc_messages: LangChain Message 列表
            stream: 是否流式响应
            temperature: 采样温度
            max_tokens: 最大输出 token 数
        
        Returns:
            响应字典或流式迭代器
        """
        # 创建 Qwen VL 视觉模型实例
        llm = create_llm(
            model="qwen",
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=stream,
            use_vl=True,  # 启用视觉模型
        )

        if stream:
            return self._stream_llm(llm, lc_messages)

        # 非流式调用
        response = llm.invoke(lc_messages)
        return self._format_response(response.content, config.qwen.vl_model)

    def _invoke_agent(
        self,
        model: str,
        lc_messages: list,
        temperature: float,
        max_tokens: Optional[int],
    ) -> dict:
        """
        非流式 Agent 调用
        
        Args:
            model: 模型名称
            lc_messages: LangChain Message 列表
            temperature: 采样温度
            max_tokens: 最大输出 token 数
        
        Returns:
            格式化后的响应字典（OpenAI 兼容格式）
        """
        # 创建 Agent 实例
        agent = self._create_agent(model, temperature, max_tokens, streaming=False)
        
        # 调用 Agent 获取结果
        result = agent.invoke({"messages": lc_messages})
        
        # 提取最终响应内容（跳过工具调用中间消息）
        final_messages = result.get("messages", [])
        content = self._extract_final_content(final_messages)
        
        # 获取实际模型名称
        model_name = config.deepseek.model if model == "deepseek" else config.qwen.model
        
        return self._format_response(content, model_name)

    def _stream_agent(
        self,
        model: str,
        lc_messages: list,
        temperature: float,
        max_tokens: Optional[int],
    ) -> Iterator[dict]:
        """
        流式 Agent 调用
        
        Args:
            model: 模型名称
            lc_messages: LangChain Message 列表
            temperature: 采样温度
            max_tokens: 最大输出 token 数
        
        Yields:
            流式响应块（OpenAI 兼容格式）
        """
        # 创建支持流式的 Agent 实例
        agent = self._create_agent(model, temperature, max_tokens, streaming=True)
        request_id = str(uuid.uuid4())

        # 流式迭代 Agent 输出
        for event in agent.stream(
            {"messages": lc_messages},
            stream_mode="messages",
        ):
            msg, _metadata = event
            
            # 过滤：只处理 AI 消息，跳过工具调用消息
            if not isinstance(msg, (AIMessage, AIMessageChunk)):
                continue
            if msg.tool_calls:
                continue
            content = msg.content
            if not content or not isinstance(content, str):
                continue
            
            # 格式化并输出
            yield self._format_stream_chunk(content, request_id)

    def _stream_llm(self, llm, lc_messages: list) -> Iterator[dict]:
        """
        直接流式调用 LLM（用于视觉模型场景）
        
        Args:
            llm: LangChain LLM 实例
            lc_messages: LangChain Message 列表
        
        Yields:
            流式响应块
        """
        request_id = str(uuid.uuid4())
        for chunk in llm.stream(lc_messages):
            content = chunk.content
            if content and isinstance(content, str):
                yield self._format_stream_chunk(content, request_id)

    @staticmethod
    def _extract_final_content(messages: list) -> str:
        """
        从 Agent 输出的消息列表中提取最终响应内容
        
        Agent 执行过程中会产生多条消息（思考、工具调用、最终回复），
        此方法从后往前查找第一个没有工具调用的 AI 消息。
        
        Args:
            messages: LangChain Message 列表
        
        Returns:
            最终回复内容字符串
        """
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                return msg.content if isinstance(msg.content, str) else str(msg.content)
        return ""

    @staticmethod
    def _format_response(content: str, model: str) -> dict:
        """
        格式化非流式响应为 OpenAI 兼容格式
        
        Args:
            content: 响应内容
            model: 模型名称
        
        Returns:
            OpenAI 兼容格式的响应字典
        """
        return {
            "id": str(uuid.uuid4()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    @staticmethod
    def _format_stream_chunk(content: str, request_id: str) -> dict:
        """
        格式化流式响应块为 OpenAI 兼容格式
        
        Args:
            content: 响应片段内容
            request_id: 请求唯一标识
        
        Returns:
            流式响应块字典
        """
        return {
            "id": request_id,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": content},
                    "finish_reason": None,
                }
            ],
        }


# 全局单例实例 - 整个应用共享一个 AgentService
agent_service = AgentService()
