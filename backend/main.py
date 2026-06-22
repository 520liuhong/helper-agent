"""
Agent智能体系统 - 主入口
FastAPI应用配置和路由注册

架构说明：
- 基于 FastAPI + LangChain/LangGraph 构建的 AI Agent 对话系统
- 采用分层架构：API层 → Agent层 → LLM服务层
- 支持 DeepSeek 和 Qwen 双模型切换
- 支持工具调用（计算器、时间、文件读取、联网搜索）
- 支持多模态（图片理解）
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# 导入核心模块
from config import config  # 配置管理
from database import init_db  # 数据库初始化
from api import chat, sessions, upload  # API路由模块


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理（FastAPI 0.19+ 新特性）
    
    启动阶段：
    1. 初始化SQLite数据库表（sessions、messages）
    2. 创建上传文件目录
    
    关闭阶段：
    - 目前无需特殊清理操作
    """
    print("Agent智能体系统启动...")
    init_db()
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
    yield
    print("Agent智能体系统关闭...")


# 创建 FastAPI 应用实例
app = FastAPI(
    title="Agent智能体系统 API",
    description="基于 LangChain Agent 的 AI 对话系统后端 API\n\n"
                "**核心功能**:\n"
                "- 支持 DeepSeek / Qwen 双模型\n"
                "- LangGraph ReAct Agent 工具调用\n"
                "- 流式与非流式响应\n"
                "- 会话持久化存储\n"
                "- 文件上传与多模态支持",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置 CORS（跨域资源共享）
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,  # 允许的前端域名列表
    allow_credentials=True,              # 允许携带Cookie
    allow_methods=["*"],                 # 允许所有HTTP方法
    allow_headers=["*"],                 # 允许所有请求头
)

# 注册 API 路由
app.include_router(chat.router, prefix="/api", tags=["聊天"])
app.include_router(sessions.router, prefix="/api", tags=["会话管理"])
app.include_router(upload.router, prefix="/api", tags=["文件上传"])

# 挂载上传文件静态目录
# 前端可通过 /uploads/{filename} 访问已上传的文件
upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


@app.get("/")
async def root():
    """根路径 - 返回系统信息"""
    return {"message": "Agent智能体系统 API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """健康检查接口 - 用于服务监控"""
    return {"status": "healthy"}


if __name__ == "__main__":
    """
    开发环境运行入口
    
    启动命令: python main.py
    访问地址: http://localhost:8000
    API文档: http://localhost:8000/docs
    """
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
