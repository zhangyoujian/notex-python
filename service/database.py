from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine
from config import configer

# 创建异步引擎
async_engine = create_async_engine(
    url=configer.mysql_url,
    pool_pre_ping=True,             # 保持启用，但需配合回收
    pool_recycle=3600,              # 回收超过 1 小时的连接（应小于 MySQL 的 wait_timeout）
    echo=False,                     # 可选：输出SQL日志
    pool_size=10,                   # 设置连接池中保持的持久连接数
    max_overflow=20                 # 设置连接池允许创建的额外连接数
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# 依赖项，用于获取数据库会话
async def get_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
