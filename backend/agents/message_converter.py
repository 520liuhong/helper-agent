"""
消息格式转换
将 API 请求消息转换为 LangChain Message 对象，支持多模态图片
"""
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from services.message_utils import (
    extract_attachments_from_content,
    is_image_file,
    resolve_image_path,
)


def _image_to_langchain_part(url: str) -> dict | None:
    """将图片 URL 转为 LangChain 多模态 content part"""
    local_path = resolve_image_path(url)
    if local_path:
        return {"type": "image_url", "image_url": {"url": f"file://{local_path}"}}
    if url.startswith("http://") or url.startswith("https://"):
        return {"type": "image_url", "image_url": {"url": url}}
    return None


def _build_human_content(msg: dict) -> str | list:
    """构建 HumanMessage 的 content（纯文本或多模态）"""
    content = msg.get("content", "")
    attachments = list(msg.get("attachments") or [])

    if isinstance(content, str) and not attachments:
        content, parsed = extract_attachments_from_content(content)
        attachments.extend(parsed)

    image_attachments = [
        att
        for att in attachments
        if att.get("type") == "image" or is_image_file(att.get("filename", ""))
    ]

    if not image_attachments:
        return content if isinstance(content, str) else str(content)

    parts: list[dict] = []
    text = content.strip() if isinstance(content, str) else ""
    if text:
        parts.append({"type": "text", "text": text})
    else:
        parts.append({"type": "text", "text": "请描述这张图片的内容"})

    for att in image_attachments:
        part = _image_to_langchain_part(att.get("url", ""))
        if part:
            parts.append(part)

    return parts if len(parts) > 1 or any(p.get("type") == "image_url" for p in parts) else text


def to_langchain_messages(messages: list[dict]) -> tuple[list[BaseMessage], bool]:
    """
    将 API 消息列表转为 LangChain Message 列表

    Returns:
        (langchain_messages, has_images)
    """
    result: list[BaseMessage] = []
    has_images = False

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            result.append(SystemMessage(content=content if isinstance(content, str) else str(content)))
        elif role == "assistant":
            result.append(AIMessage(content=content if isinstance(content, str) else str(content)))
        elif role == "user":
            human_content = _build_human_content(msg)
            if isinstance(human_content, list):
                has_images = True
            result.append(HumanMessage(content=human_content))
        else:
            result.append(HumanMessage(content=content if isinstance(content, str) else str(content)))

    return result, has_images
