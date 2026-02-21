import google.genai as genai
from typing import Optional, List, Dict, Any
from utils import logger
from config import configer


class GeminiService:
    def __init__(self):
        if not configer.google_api_key:
            logger.warning("GOOGLE_API_KEY not set. Gemini service will not work.")
            self.client = None
            return

        # 创建客户端
        self.client = genai.Client(api_key=configer.google_api_key)
        # 确定使用的模型名称
        self.model_name = (
            configer.openai_model
            if "gemini" in configer.openai_model
            else "gemini-1.5-flash"
        )

    async def generate_text(self, prompt: str) -> str:
        if self.client is None:
            return "Error: GOOGLE_API_KEY not set."

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            return f"Error generating text: {str(e)}"

    async def generate_chat(self, history: List[Dict[str, Any]], message: str) -> str:
        """
        history format (旧格式): [{"role": "user", "parts": ["msg"]}, ...]
        转换为新格式: [{"role": "user", "parts": [{"text": "msg"}]}, ...]
        """
        if self.client is None:
            return "Error: GOOGLE_API_KEY not set."

        try:
            # 转换历史记录格式以适应 google.genai
            converted_history = []
            for item in history:
                role = item["role"]
                # 假设 parts 列表的第一个元素为文本内容
                parts = [{"text": item["parts"][0]}] if item.get("parts") else []
                converted_history.append({"role": role, "parts": parts})

            # 创建聊天会话并传入历史记录
            chat = self.client.aio.chats.create(
                model=self.model_name,
                history=converted_history
            )
            # 发送新消息
            response = await chat.send_message(message)
            return response.text
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            return f"Error generating chat response: {str(e)}"


# 全局单例实例
gemini_service = GeminiService()


def get_gemini_service():
    return gemini_service