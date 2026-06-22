"""
文件上传API路由
支持阿里云OSS和本地存储两种方式
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import os
import uuid
from datetime import datetime
import aiofiles

from config import config

router = APIRouter()

# 本地存储目录
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")


class UploadResponse(BaseModel):
    """上传响应模型"""
    url: str
    filename: str
    size: int
    type: str  # "oss" or "local"


def ensure_upload_dir():
    """确保上传目录存在"""
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    文件上传接口
    优先使用阿里云OSS，如果未配置则使用本地存储
    """
    # 生成唯一文件名
    ext = file.filename.split(".")[-1] if "." in file.filename else ""
    date_str = datetime.now().strftime('%Y%m%d')
    file_id = uuid.uuid4().hex
    unique_filename = f"{date_str}/{file_id}.{ext}"

    try:
        # 读取文件内容
        content = await file.read()
        file_size = len(content)

        # 检查文件大小限制 (10MB)
        max_size = 10 * 1024 * 1024
        if file_size > max_size:
            raise HTTPException(status_code=400, detail="文件大小不能超过10MB")

        # 如果配置了OSS，使用OSS上传
        if config.oss:
            try:
                import oss2
                auth = oss2.Auth(config.oss.access_key_id, config.oss.access_key_secret)
                bucket = oss2.Bucket(auth, config.oss.endpoint, config.oss.bucket_name)

                result = bucket.put_object(unique_filename, content)

                if result.status == 200:
                    # 生成文件URL
                    file_url = f"https://{config.oss.bucket_name}.{config.oss.endpoint}/{unique_filename}"
                    return UploadResponse(
                        url=file_url,
                        filename=file.filename,
                        size=file_size,
                        type="oss",
                    )
                else:
                    raise HTTPException(status_code=500, detail="上传到OSS失败")
            except Exception as e:
                # OSS上传失败，尝试使用本地存储
                print(f"OSS上传失败，切换到本地存储: {e}")

        # 使用本地存储
        ensure_upload_dir()
        date_dir = os.path.join(UPLOAD_DIR, date_str)
        if not os.path.exists(date_dir):
            os.makedirs(date_dir, exist_ok=True)

        file_path = os.path.join(date_dir, f"{file_id}.{ext}")

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        # 生成文件URL (相对路径)
        file_url = f"/uploads/{unique_filename}"

        return UploadResponse(
            url=file_url,
            filename=file.filename,
            size=file_size,
            type="local",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("/uploads/{filename}")
async def get_upload(filename: str):
    """获取上传的文件"""
    from fastapi.responses import FileResponse
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="文件不存在")
