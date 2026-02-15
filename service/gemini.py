import google.generativeai as genai
from typing import Optional
from utils import logger
from config import configer


class GeminiService:
    def __init__(self):
        if not configer.google_api_key:
            logger.warning("GOOGLE_API_KEY not set. Gemini service will not work.")
            return

        genai.configure(api_key=configer.google_api_key)
        self.model = genai.GenerativeModel(
            configer.openai_model if "gemini" in configer.openai_model else "gemini-1.5-flash")

    async def generate_text(self, prompt: str) -> str:
        if not configer.google_api_key:
            return "Error: GOOGLE_API_KEY not set."

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            return f"Error generating text: {str(e)}"

    async def generate_chat(self, history: list, message: str) -> str:
        # history format: [{"role": "user", "parts": ["msg"]}, ...]
        if not configer.google_api_key:
            return "Error: GOOGLE_API_KEY not set."

        try:
            chat = self.model.start_chat(history=history)
            response = await chat.send_message_async(message)
            return response.text
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            return f"Error generating chat response: {str(e)}"


gemini_service = GeminiService()


def get_gemini_service():
    return gemini_service
