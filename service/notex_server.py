import asyncio
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from config import configer
from utils import logger
from .vector_store import AsyncVectorStore
from .agent import NotexAgent
from crud.source import db_list_sources

class NotexServer:

    def __init__(self):
        self.vector_store = AsyncVectorStore()
        self.agent = NotexAgent()
        self.lock = asyncio.Lock()
        self.loaded_notex_books = {}

    async def load_notebook_vector_index(self, notebook_id: str, db: AsyncSession):
        async with self.lock:
            if self.loaded_notex_books.get(notebook_id, False):
                return

            sources = await db_list_sources(db, notebook_id)
            for source in sources:
                await self.vector_store.ingest_text(notebook_id, source.name, source.content)

            self.loaded_notex_books[notebook_id] = True

            stats = await self.vector_store.get_stats()

            logger.info(f"✅ notebook {notebook_id} loaded into vector store ({stats.total_documents} total documents)")

notex_server = NotexServer()

def get_notex_server():
    return notex_server