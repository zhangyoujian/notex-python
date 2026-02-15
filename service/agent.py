import logging
from config import configer
from models import ChatMessage
from .openai import get_openai_service
from .gemini import get_gemini_service
from utils import logger
from schemas.chat import ChatResponse


class NotexAgent:
    def __init__(self):
        self.llm = self._create_llm()

    @staticmethod
    def _create_llm():
        if configer.openai_api_key and configer.openai_base_url:
            return get_openai_service()
        if configer.openai_api_key and not configer.openai_base_url:
            return get_openai_service()
        if configer.google_api_key:
            return get_gemini_service()
        logger.warning("No LLM provider configured. Set OPENAI_API_KEY or GOOGLE_API_KEY.")
        return None

    async def generate_chat(self, notebook_id: str, message: str, history: list[ChatMessage]) ->str:

        await self.llm.generate_chat(history, message)

    async def generate_text(self, prompt: str) -> str:

        await self.llm.generate_text(prompt)
