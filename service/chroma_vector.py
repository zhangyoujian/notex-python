import os
import uuid
import chromadb
from chromadb.api import Collection, ClientAPI
from chromadb.config import Settings
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from typing import List, Dict, Any

from sympy.codegen.ast import Raise

from config import configer
from utils import logger
from utils.convert import *
from .embedding import EmbeddingModel


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


class ChromaVector:
    """异步向量存储管理器"""

    def __init__(self, is_ollama: bool = False, dist=0.3):
        self._dist = dist
        self._embedding_model = EmbeddingModel(configer.embedding_model_url,
                                               configer.embedding_model_name,
                                               is_ollama,
                                               "EMPTY")

        self._client = chromadb.PersistentClient(
            path=configer.vector_store_path,
            settings=Settings(anonymized_telemetry=False)
        )

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


    async def ingest_documents(self, notebook_id: str, paths: List[str]) -> None:
        """批量摄入文档文件"""
        for path in paths:
            logger.debug(f"[ChromaStore] Loading file: {path}")
            content = await extract_from_file(path)
            logger.debug(f"[ChromaStore] File loaded, size: {len(content)} bytes")
            source_name = os.path.basename(path)
            self.ingest_text(notebook_id, source_name, content)


    def ingest_text(self, notebook_id: str, source_name: str, content: str) -> int:
        """摄入原始文本，分块后存入 ChromaDB"""
        chunks = self._split_text(content)
        if not chunks:
            return 0

        ids = []
        documents = []
        metadatas = []
        for idx, chunk in enumerate(chunks):
            doc_id = f"{notebook_id}::{source_name}::chunk{idx}::{uuid.uuid4().hex[:8]}"
            ids.append(doc_id)
            documents.append(chunk)
            metadatas.append({
                "notebook_id": notebook_id,
                "source": source_name,
                "chunk_index": idx
            })

        collection = self._client.get_or_create_collection(name=notebook_id,
                                                           embedding_function=self._embedding_model.get_embedding_model(),
                                                           metadata = {"hnsw:space": "cosine"})

        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        logger.info(f"[ChromaStore] Ingested {len(chunks)} chunks from source '{source_name}'")
        return len(chunks)

    # -------------------- 相似性搜索--------------------
    def similarity_search(self, notebook_id: str, query: str, num_docs: int = 10) -> List[Document]:
        """基于向量相似度的搜索，通过 notebook_id 过滤"""
        collection = self._client.get_collection(name=notebook_id)
        if not collection:
            return []

        # 查询 ChromaDB
        results = collection.query(
            query_texts=[query],
            n_results=num_docs,
            where={"notebook_id": notebook_id},
            include=["documents", "metadatas", "distances"]
        )

        # 转换为 Document 列表
        docs = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
                if dist <= self._dist:
                    docs.append(Document(page_content=doc, metadata=meta))

        return docs

    def delete(self, notebook_id: str, source: str) -> None:

        if not source or source == "":
            self._client.delete_collection(name=notebook_id)

        collection = self._client.get_collection(name=notebook_id)
        if not collection:
            raise ValueError(f"[ChromaStore] Collection not found: {notebook_id}")

        collection.delete(where={"source": source})

    def get_stats(self, notebook_id: str) -> VectorStats:
        """获取当前集合的统计信息"""
        collection = self._client.get_collection(name=notebook_id)
        if not collection:
            raise ValueError(f"[ChromaStore] Collection not found: {notebook_id}")

        count = collection.count()
        dim = self._embedding_model.get_embedding_dim()
        return VectorStats(total_documents=count, total_vectors=count, dimension=dim)
