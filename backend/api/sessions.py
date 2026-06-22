"""
会话管理API路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid
import json

from database import get_connection, init_db

router = APIRouter()


class Session(BaseModel):
    """会话模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(default="新会话")
    messages: list[dict] = Field(default_factory=list)
    model: str = Field(default="deepseek")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


def _now() -> str:
    return datetime.now().isoformat()


def _message_to_dict(row) -> dict:
    message = {
        "role": row["role"],
        "content": row["content"],
    }
    attachments = json.loads(row["attachments"] or "[]")
    if attachments:
        message["attachments"] = attachments
    return message


def _ensure_session_exists(conn, session_id: str):
    session = conn.execute(
        "SELECT id FROM sessions WHERE id = ?",
        (session_id,),
    ).fetchone()
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")


@router.get("/sessions")
async def list_sessions():
    """获取所有会话列表"""
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                s.id,
                s.title,
                s.model,
                s.created_at,
                s.updated_at,
                COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            """
        ).fetchall()

    sessions = [dict(row) for row in rows]
    return {"sessions": sessions}


@router.post("/sessions")
async def create_session(session: Optional[Session] = None):
    """创建新会话"""
    init_db()
    if session is None:
        session = Session()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, title, model, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session.id,
                session.title,
                session.model,
                session.created_at,
                session.updated_at,
            ),
        )
    return {
        "id": session.id,
        "title": session.title,
        "model": session.model,
        "created_at": session.created_at,
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """获取指定会话"""
    init_db()
    with get_connection() as conn:
        session = conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if session is None:
            raise HTTPException(status_code=404, detail="会话不存在")

        messages = conn.execute(
            """
            SELECT role, content, attachments
            FROM messages
            WHERE session_id = ?
            ORDER BY position ASC
            """,
            (session_id,),
        ).fetchall()

    return {
        "id": session["id"],
        "title": session["title"],
        "model": session["model"],
        "messages": [_message_to_dict(row) for row in messages],
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
    }


@router.put("/sessions/{session_id}")
async def update_session(session_id: str, session: Session):
    """更新会话"""
    init_db()
    updated_at = _now()
    title = session.title
    if session.messages and session.messages[0].get("role") == "user":
        content = session.messages[0].get("content", "")
        title = content[:20] + ("..." if len(content) > 20 else "")

    with get_connection() as conn:
        _ensure_session_exists(conn, session_id)
        conn.execute(
            """
            UPDATE sessions
            SET title = ?, model = ?, updated_at = ?
            WHERE id = ?
            """,
            (title, session.model, updated_at, session_id),
        )
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        for index, message in enumerate(session.messages):
            conn.execute(
                """
                INSERT INTO messages (
                    id, session_id, role, content, attachments, position, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    session_id,
                    message.get("role", "user"),
                    message.get("content", ""),
                    json.dumps(message.get("attachments", []), ensure_ascii=False),
                    index,
                    updated_at,
                ),
            )
    return {"message": "更新成功"}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    init_db()
    with get_connection() as conn:
        _ensure_session_exists(conn, session_id)
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    return {"message": "删除成功"}


@router.post("/sessions/{session_id}/messages")
async def add_message(session_id: str, message: dict):
    """添加消息到会话"""
    init_db()
    updated_at = _now()
    with get_connection() as conn:
        _ensure_session_exists(conn, session_id)
        position = conn.execute(
            "SELECT COUNT(*) AS count FROM messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()["count"]

        conn.execute(
            """
            INSERT INTO messages (
                id, session_id, role, content, attachments, position, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                session_id,
                message.get("role", "user"),
                message.get("content", ""),
                json.dumps(message.get("attachments", []), ensure_ascii=False),
                position,
                updated_at,
            ),
        )

        title = None
        if position == 0 and message.get("role") == "user":
            content = message.get("content", "")
            title = content[:20] + ("..." if len(content) > 20 else "")
            conn.execute(
                """
                UPDATE sessions
                SET title = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, updated_at, session_id),
            )
        else:
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (updated_at, session_id),
            )

    return {"message": "添加成功", "title": title, "updated_at": updated_at}
