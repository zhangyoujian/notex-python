import os.path
import time
import io
import uuid
from pathlib import Path

import aiofiles
import json
from fastapi import APIRouter, Request,UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import configer
from service.auth import get_current_user
from service.database import get_session
from service.notex_server import get_notex_server, NotexServer

from utils import logger
from models.source import Source
from models.users import User
from crud.source import db_create_source, db_update_source_chunk_count
from routers.notebooks import get_source_info
from utils.convert import extract_from_file

from utils.response import success_response


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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create uploads directory")

    # 完整保存路径
    temp_path = user_upload_dir / unique_filename
    try:
        content = await file.read()
        async with aiofiles.open(temp_path, "wb") as f:
            await f.write(content)
    except Exception as e:
        logger.error(f"Failed to save file: {unique_filename}, error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save file: {str(e)}")

    logger.info(f"unique_file: {unique_filename}, full_path: {str(temp_path)}")
    return unique_filename, str(temp_path)

# 创建路由组
router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


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
                      notex_server: NotexServer = Depends(get_notex_server)):
    from .notebooks import check_notebook_access
    await check_notebook_access(user.id, notebook_id, db)

    unique_filename, full_path = await save_user_file(user.id, file)
    content = await extract_from_file(full_path)
    metadata_ = {
        "path": os.path.basename(full_path),
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

    chunk_count = notex_server.vector_store.ingest_text(notebook_id, source.name, source.content)

    await db_update_source_chunk_count(db, source.id, chunk_count)

    source.chunk_count = chunk_count

    return success_response(code=status.HTTP_201_CREATED, message="上传成功", data=get_source_info(source))
