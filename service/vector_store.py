import os

import aiofiles
import asyncio
import chromadb
from chromadb.api.async_api import AsyncCollection, AsyncClientAPI
from chromadb.config import Settings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from typing import List, Dict, Any
from config import configer
from utils import logger
import uuid


@dataclass
class Document:
    """文档模型"""
    page_content: str
    metadata: Dict[str, Any]


class VectorStats(BaseModel):
    """统计信息"""
    total_documents: int
    total_vectors: int
    dimension: int


class AsyncVectorStore:
    """异步向量存储管理器，对标 Go 的 VectorStore"""

    def __init__(self, is_ollama: bool = False):
        self.is_ollama = is_ollama
        self._client: Optional[AsyncClientAPI] = None
        self._collection: Optional[AsyncCollection] = None
        self._embedding_function = self._create_embedding_function()

    def _create_embedding_function(self):
        """创建 ChromaDB 嵌入函数"""
        if self.is_ollama:
            # 示例：使用 Ollama 嵌入，需自行实现或使用 langchain 的 OllamaEmbeddings
            # 这里简化为 SentenceTransformer，实际可替换
            from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
            return OllamaEmbeddingFunction(model_name="nomic-embed-text", url="http://localhost:11434/api/embeddings")
        else:
            return SentenceTransformerEmbeddingFunction(model_name=configer.embedding_model)

    async def initialize(self):
        """初始化 ChromaDB 异步客户端和集合（每个 notebook 一个集合）"""
        self._client = await chromadb.AsyncPersistentClient(
            path=configer.vector_store_path,
            settings=Settings(anonymized_telemetry=False)
        )
        # 这里我们不预创建集合，而是在操作时动态获取/创建
        # 可设计为根据 notebook_id 管理不同集合，或单集合+过滤
        # 为保持简单，使用单集合 + 元数据过滤
        self._collection = await self._client.get_or_create_collection(
            name="notebook_vectors",
            embedding_function=self._embedding_function,
            metadata={"hnsw:space": "cosine"}
        )

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.close()

    # -------------------- 文档提取与转换--------------------
    async def extract_document(self, path: str) -> str:
        """读取本地文件，若需转换则调用 markitdown"""
        ext = os.path.splitext(path)[1].lower()
        if configer.enable_markitdown and self._needs_markitdown(ext):
            return await self._convert_with_markitdown(path)
        # 普通文本文件异步读取
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            return await f.read()

    @staticmethod
    def _needs_markitdown(ext: str) -> bool:
        """判断是否需要 markitdown 转换"""
        markitdown_exts = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls"}
        return ext in markitdown_exts

    @staticmethod
    async def _convert_with_markitdown(file_path: str) -> str:
        """异步调用 markitdown 命令行转换文档为 Markdown"""
        tmp_file = os.path.join(os.path.dirname(file_path), f"__markitdown_{os.path.basename(file_path)}.md")
        cmd = [configer.markitdown_cmd, file_path, "-o", tmp_file]
        process = await asyncio.create_subprocess_exec(*cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"markitdown failed: {stderr.decode()}")
        async with aiofiles.open(tmp_file, "r", encoding="utf-8") as f:
            content = await f.read()
        os.unlink(tmp_file)  # 同步删除，可改用 aiofiles 异步删除
        return content

    @staticmethod
    async def extract_from_url(url: str) -> str:
        """从 URL 获取内容并转换"""
        if not configer.enable_markitdown:
            raise RuntimeError("markitdown is disabled, cannot fetch URL content")
        tmp_file = f"/tmp/markitdown_url_{uuid.uuid4().hex}.md"
        cmd = [configer.markitdown_command, url, "-o", tmp_file]
        process = await asyncio.create_subprocess_exec(*cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"markitdown URL conversion failed: {stderr.decode()}")
        async with aiofiles.open(tmp_file, "r", encoding="utf-8") as f:
            content = await f.read()
        os.unlink(tmp_file)
        return content

    # -------------------- 文本分块--------------------
    @staticmethod
    def _split_text(text: str) -> List[str]:
        """将文本切分为块，支持 CJK 与西文混合"""
        chunk_size = configer.chunk_size
        chunk_overlap = configer.chunk_overlap

        if not text:
            return []

        # 检测 CJK 比例
        runes = list(text)
        cjk_count = 0
        sample = runes[:1000]
        for ch in sample:
            if '\u4e00' <= ch <= '\u9fff':  # CJK 统一表意字符
                cjk_count += 1
        cjk_ratio = cjk_count / len(sample) if sample else 0

        chunks = []
        if cjk_ratio > 0.3:
            # CJK 按字符数切分
            step = chunk_size - chunk_overlap
            for i in range(0, len(runes), step):
                end = i + chunk_size
                chunks.append(''.join(runes[i:end]))
                if end >= len(runes):
                    break
        else:
            # 西文按单词切分
            words = text.split()
            step = chunk_size - chunk_overlap
            for i in range(0, len(words), step):
                end = i + chunk_size
                chunks.append(' '.join(words[i:end]))
                if end >= len(words):
                    break
        return chunks

    # -------------------- 数据摄入）--------------------
    async def ingest_documents(self, notebook_id: str, paths: List[str]) -> None:
        """批量摄入文档文件"""
        for path in paths:
            logger.info(f"[VectorStore] Loading file: {path}")
            content = await self.extract_document(path)
            logger.info(f"[VectorStore] File loaded, size: {len(content)} bytes")
            source_name = os.path.basename(path)
            await self.ingest_text(notebook_id, source_name, content)

    async def ingest_text(self, notebook_id: str, source_name: str, content: str) -> int:
        """摄入原始文本，分块后存入 ChromaDB"""
        chunks = self._split_text(content)
        if not chunks:
            return 0

        ids = []
        documents = []
        metadatas_ = []
        for idx, chunk in enumerate(chunks):
            doc_id = f"{notebook_id}::{source_name}::chunk{idx}::{uuid.uuid4().hex[:8]}"
            ids.append(doc_id)
            documents.append(chunk)
            metadatas_.append({
                "notebook_id": notebook_id,
                "source": source_name,
                "chunk_index": idx
            })

        # 异步批量添加
        await self._collection.add(documents=documents, metadatas=metadatas_, ids=ids)
        logger.info(f"[VectorStore] Ingested {len(chunks)} chunks from source '{source_name}'")
        return len(chunks)

    # -------------------- 相似性搜索--------------------
    async def similarity_search(self, notebook_id: str, query: str, num_docs: int = 5) -> List[Document]:
        """基于向量相似度的搜索，通过 notebook_id 过滤"""
        if num_docs <= 0:
            num_docs = 5

        # 查询 ChromaDB
        results = await self._collection.query(
            query_texts=[query],
            n_results=num_docs,
            where={"notebook_id": notebook_id},
            include=["documents", "metadatas", "distances"]
        )

        # 转换为 Document 列表
        docs = []
        if results["documents"] and results["documents"][0]:
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                docs.append(Document(page_content=doc, metadata=meta))
        return docs

    async def delete(self, source: str) -> None:
        await self._collection.delete(where={"source": source})

    async def get_stats(self) -> VectorStats:
        """获取当前集合的统计信息"""
        count = await self._collection.count()
        # 维度从嵌入函数获取（若支持）
        dim = 1536  # 默认 OpenAI 维度
        if configer.is_ollama():
            dim = 768
        else:
            # 尝试从 sentence-transformers 模型获取维度
            try:
                dim = self._embedding_function._get_model().get_sentence_embedding_dimension()
            except:
                pass
        return VectorStats(total_documents=count, total_vectors=count, dimension=dim)

vector_store = AsyncVectorStore()

def get_vector_service():
    return vector_store