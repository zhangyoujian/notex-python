from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import users, health
from utils.exception_handlers import register_exception_handlers

app = FastAPI(
    title="Notex API",
    version="1.0.0",
    description="A privacy-first, open-source alternative to NotebookLM"
)

# 注册异常处理器
register_exception_handlers(app)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # 允许的源，开发阶段允许所有源，生产环境需要指定源
    allow_credentials=True,  # 允许携带cookie
    allow_methods=["*"],     # 允许的请求方法
    allow_headers=["*"],     # 允许的请求头
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

# 挂载路由/注册路由
app.include_router(health.router)
app.include_router(users.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.SERVER_HOST, port=int(settings.SERVER_PORT), reload=True)