"""
Agent智能体系统 - 配置管理
从环境变量加载配置，支持配置验证
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# 加载 backend/.env 中的环境变量
load_dotenv(Path(__file__).resolve().parent / ".env")


class DeepSeekConfig(BaseModel):
    """DeepSeek API配置"""
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"


class QwenConfig(BaseModel):
    """Qwen API配置"""
    api_key: str
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen-turbo"
    vl_model: str = "qwen-vl-plus"


class OSSConfig(BaseModel):
    """阿里云OSS配置"""
    access_key_id: str
    access_key_secret: str
    bucket_name: str
    endpoint: str


class TavilyConfig(BaseModel):
    """Tavily 联网搜索配置"""
    api_key: str
    max_results: int = 5


class Config(BaseModel):
    """应用配置"""
    deepseek: DeepSeekConfig
    qwen: QwenConfig
    tavily: Optional[TavilyConfig] = None
    oss: Optional[OSSConfig] = None
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]


def load_config() -> Config:
    """从环境变量加载配置"""
    return Config(
        deepseek=DeepSeekConfig(
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        ),
        qwen=QwenConfig(
            api_key=os.getenv("QWEN_API_KEY", ""),
            base_url=os.getenv("QWEN_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            model=os.getenv("QWEN_MODEL", "qwen-turbo"),
            vl_model=os.getenv("QWEN_VL_MODEL", "qwen-vl-plus"),
        ),
        tavily=TavilyConfig(
            api_key=os.getenv("TAVILY_API_KEY", ""),
            max_results=int(os.getenv("TAVILY_MAX_RESULTS", "5")),
        ) if os.getenv("TAVILY_API_KEY") else None,
        oss=OSSConfig(
            access_key_id=os.getenv("ALIYUN_OSS_ACCESS_KEY_ID", ""),
            access_key_secret=os.getenv("ALIYUN_OSS_ACCESS_KEY_SECRET", ""),
            bucket_name=os.getenv("ALIYUN_OSS_BUCKET_NAME", ""),
            endpoint=os.getenv("ALIYUN_OSS_ENDPOINT", ""),
        ) if all([
            os.getenv("ALIYUN_OSS_ACCESS_KEY_ID"),
            os.getenv("ALIYUN_OSS_ACCESS_KEY_SECRET"),
            os.getenv("ALIYUN_OSS_BUCKET_NAME"),
            os.getenv("ALIYUN_OSS_ENDPOINT"),
        ]) else None,
        cors_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(","),
    )


# 全局配置实例
config = load_config()
