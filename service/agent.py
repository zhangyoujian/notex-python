import logging
from config import configer
from .openai import get_openai_service
from utils import logger


def get_agent_service():
    if configer.openai_api_key and configer.openai_base_url:
        return get_openai_service()
    if configer.openai_api_key and not configer.openai_base_url:
        return get_openai_service()
    logger.warning("No LLM provider configured. Set OPENAI_API_KEY or GOOGLE_API_KEY.")
    return get_openai_service()
