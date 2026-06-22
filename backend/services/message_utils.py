"""
消息工具：解析附件并将用户消息转换为 Qwen 多模态格式
"""
import os
import re
from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
FILE_LINK_PATTERN = re.compile(r"\[文件:\s*([^\]]+)\]\(([^)]+)\)")


def is_image_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS


def resolve_image_path(url: str) -> str | None:
    """将 /uploads/... 解析为本地绝对路径"""
    if not url.startswith("/uploads/"):
        return None
    rel = url[len("/uploads/") :]
    path = UPLOAD_DIR / rel.replace("/", os.sep)
    if path.is_file():
        return str(path.resolve())
    return None


def extract_attachments_from_content(content: str) -> tuple[str, list[dict]]:
    """从 Markdown 文件链接中解析图片附件"""
    attachments: list[dict] = []

    def replacer(match: re.Match) -> str:
        filename, url = match.group(1), match.group(2)
        if is_image_file(filename):
            attachments.append({"filename": filename, "url": url, "type": "image"})
            return ""
        return match.group(0)

    cleaned = FILE_LINK_PATTERN.sub(replacer, content).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned, attachments


def _image_source(url: str) -> str | None:
    """生成 Qwen 可识别的图片来源（file:// 或 http URL）"""
    local_path = resolve_image_path(url)
    if local_path:
        return f"file://{local_path}"
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return None


def build_qwen_messages(messages: list[dict]) -> tuple[list[dict], bool]:
    """
    将消息列表转换为 Qwen API 格式。
    含图片的用户消息会使用多模态 content 数组。
    """
    result: list[dict] = []
    has_images = False

    for msg in messages:
        role = msg["role"]
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

        if role == "user" and image_attachments:
            parts: list[dict] = []
            for att in image_attachments:
                source = _image_source(att.get("url", ""))
                if source:
                    parts.append({"image": source})

            if not parts:
                result.append({"role": role, "content": content if isinstance(content, str) else str(content)})
                continue

            has_images = True
            text = content.strip() if isinstance(content, str) else ""
            if text:
                parts.append({"text": text})
            else:
                parts.append({"text": "请描述这张图片的内容"})

            result.append({"role": role, "content": parts})
            continue

        if isinstance(content, str):
            result.append({"role": role, "content": content})
        else:
            result.append({"role": role, "content": str(content)})

    return result, has_images
