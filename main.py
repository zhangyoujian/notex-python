import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from routers import auth, api, files, notebooks, public, admin
from config import configer
from service.database import async_engine
from models.base import Base
from contextlib import asynccontextmanager
from utils.exception_handlers import register_exception_handlers
from utils import logger
from utils.redis_cache import AsyncRedisCache

VERSION = "1.0.0"


async def audit_middleware_lite(request: Request, call_next):
    # 审计逻辑
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()

    # 记录审计日志（示例）
    logger.info(f"AUDIT: {request.method} {request.url.path} - {response.status_code} - {process_time}s")
    return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：尽量完成 Redis 清理、建表、初始化；任一步失败也不阻塞应用启动，保证能响应请求
    cache = AsyncRedisCache(enable_stats=False)
    try:
        await cache.clear()
        logger.info("Redis cache cleared on startup")
    except Exception as e:
        logger.warning("Redis cache clear on startup failed: %s", e)
    finally:
        try:
            await cache.close()
        except Exception:
            pass

    # 启动时：创建表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 关闭时：清理资源
    await async_engine.dispose()


app = FastAPI(
    title="Notex API",
    version="1.0.0",
    description="A privacy-first, open-source alternative to NotebookLM",
    lifespan=lifespan
)

# 注册异常处理器
register_exception_handlers(app)

app.middleware("http")(audit_middleware_lite)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # 允许的源，开发阶段允许所有源，生产环境需要指定源
    allow_credentials=True,  # 允许携带cookie
    allow_methods=["*"],     # 允许的请求方法
    allow_headers=["*"],     # 允许的请求头
)


frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend"))
static_path = os.path.join(frontend_path, "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# 挂载路由/注册路由
app.include_router(public.router)
app.include_router(api.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(notebooks.router)


@app.get("/", response_class=HTMLResponse)
async def server_root():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers={"Cache-Control": "no-cache"})
    return HTMLResponse(content="<h1>Notex Frontend not found</h1>")


@app.get("/login", response_class=HTMLResponse)
async def get_login_page():
    index_path = os.path.join(frontend_path, "login.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers={"Cache-Control": "no-cache"})
    return HTMLResponse(content="<h1>Notex Frontend not found</h1>")


@app.get("/register", response_class=HTMLResponse)
async def get_register_page():
    index_path = os.path.join(frontend_path, "register.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers={"Cache-Control": "no-cache"})
    return HTMLResponse(content="<h1>Notex Frontend not found</h1>")


@app.get("/notes/{note_id}", response_class=HTMLResponse)
async def server_note(note_id: str):
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers={"Cache-Control": "no-cache"})
    return HTMLResponse(content="<h1>Notex Frontend not found</h1>")


@app.get("/public/{token}", response_class=HTMLResponse)
async def server_public(token: str):
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers={"Cache-Control": "no-cache"})
    return HTMLResponse(content="<h1>Notex Frontend not found</h1>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=configer.server_host, port=int(configer.server_port), reload=True)