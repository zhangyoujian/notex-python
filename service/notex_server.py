import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from config import configer
from utils import logger
from .chroma_vector import ChromaVector
from .agent import NotexAgent
from crud.source import db_list_sources

class NotexServer:

    def __init__(self):
        self.vector_store = ChromaVector()
        self.agent = NotexAgent()
        self.lock = asyncio.Lock()
        self.loaded_notex_books = {}

    async def load_notebook_vector_index(self, notebook_id: str, db: AsyncSession):

        # 从数据库加载向量数据
        async with self.lock:
            if self.loaded_notex_books.get(notebook_id, False):
                return

            sources = await db_list_sources(db, notebook_id)
            for source in sources:
                await self.vector_store.ingest_text(notebook_id, source.name, source.content)

            self.loaded_notex_books[notebook_id] = True

            stats = await self.vector_store.get_stats(notebook_id)

            logger.info(f"notebook {notebook_id} loaded into vector store ({stats.total_documents} total documents)")

    async def remove_notebook_vector_index(self, notebook_id: str):
        async with self.lock:
            if self.loaded_notex_books.get(notebook_id, False):
                self.loaded_notex_books.pop(notebook_id)
                await self.vector_store.delete(notebook_id, "")


notex_server = NotexServer()

def get_notex_server():
    return notex_server