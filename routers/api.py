import time
import io
from datetime import datetime
import uuid
from pathlib import Path

import aiofiles
import json
from fastapi import APIRouter, Request,UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import configer
from service.auth import get_current_user
from service.database import get_session
from service.vector_store import AsyncVectorStore, get_vector_service
from utils import logger
from models.source import Source
from models.users import User
from crud.source import db_create_source, db_update_source_chunk_count
from routers.notebooks import get_source_info

from utils.response import success_response


async def audit_middleware_lite(request: Request, call_next):
    # 审计逻辑
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()

    # 记录审计日志（示例）
    logger.info(f"AUDIT: {request.method} {request.url.path} - {response.status_code} - {process_time}s")
    return response


async def save_user_file(user_id: int, file: UploadFile):

    p = Path(file.filename)
    ext = p.suffix
    base_name = p.stem
    unique_filename = f"{base_name}_{uuid.uuid4().hex[:8]}{ext}"

    # 用户专属上传目录
    user_upload_dir = Path(f"{configer.upload_path}/{user_id}")
    try:
        user_upload_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create user uploads directory: {e}")
        raise HTTPException(status_code=500, detail="Failed to create uploads directory")

    # 完整保存路径
    temp_path = user_upload_dir / unique_filename
    try:
        content = await file.read()
        async with aiofiles.open(temp_path, "wb") as f:
            await f.write(content)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    return unique_filename, temp_path.name

# 创建路由组
router = APIRouter(prefix="/api", dependencies=[Depends(audit_middleware_lite), Depends(get_current_user)])


@router.get("/health")
async def health_check():
    content = {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": time.monotonic(),
        "services": {
            "vector_store": configer.vector_store_type,
            "llm": configer.openai_model
        }
    }
    return success_response(data=content)


@router.get("/config")
async def get_config():
    return success_response(message="获取服务器配置信息成功", data={})


@router.post("/upload")
async def upload_file(file: UploadFile = File(...),
                      notebook_id: str = Form(...),
                      user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_session),
                      vector_service: AsyncVectorStore = Depends(get_vector_service)):
    from .notebooks import check_notebook_access
    await check_notebook_access(user.id, notebook_id, db)

    unique_filename, temp_path = await save_user_file(user.id, file)
    content = await vector_service.extract_document(temp_path)
    metadata_ = {
        "path": temp_path,
        "user_id": user.id
    }
    source = await db_create_source(db,
                              notebook_id,
                              file.filename,
                              "file",
                               "",
                              content,
                              unique_filename,
                              file.size,
                              0,
                              json.dumps(metadata_))

    stats = await vector_service.get_stats()

    total_docs_before = stats.total_documents

    await vector_service.ingest_text(notebook_id, source.name, source.content)

    stats = await vector_service.get_stats()

    chunk_count = stats.total_documents - total_docs_before

    await db_update_source_chunk_count(db, source.id, chunk_count)

    source.chunk_count = chunk_count

    return success_response(code=status.HTTP_201_CREATED, message="上传成功", data={get_source_info(source)})
