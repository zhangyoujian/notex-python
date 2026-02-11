import time
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from config import configer
from service.auth import get_current_user
from utils import logger

from utils.response import success_response


async def audit_middleware_lite(request: Request, call_next):
    # 审计逻辑
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()

    # 记录审计日志（示例）
    logger.info(f"AUDIT: {request.method} {request.url.path} - {response.status_code} - {process_time}s")
    return response

# 创建路由组
router = APIRouter(
    prefix="/api",
    dependencies=[Depends(audit_middleware_lite), Depends(get_current_user)]
)


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
    return success_response(data={})
