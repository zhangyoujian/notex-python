import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
from config import configer
from utils import logger
import uuid


class VectorService:
    def __init__(self):
        # Use persistent client
        self.client = chromadb.PersistentClient(path="./data/chroma_db")
        self.collection = self.client.get_or_create_collection(name="notex_documents")

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str] = None):
        if not ids:
            ids = [str(uuid.uuid4()) for _ in texts]

        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        return ids

    def search(self, query: str, notebook_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where={"notebook_id": notebook_id}
        )

        # Format results
        # Chroma returns lists of lists
        formatted_results = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                formatted_results.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "id": results["ids"][0][i]
                })

        return formatted_results

    def delete_notebook_docs(self, notebook_id: str):
        self.collection.delete(
            where={"notebook_id": notebook_id}
        )


vector_service = VectorService()


def get_vector_service():
    return vector_service
