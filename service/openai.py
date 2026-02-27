from fastapi import HTTPException, status
from typing import List, Dict, Any, Optional
import httpx
from config import configer
from utils import logger


class OpenAIService:
    def __init__(self):
        self.api_key: Optional[str] = configer.openai_api_key
        self.base_url: str = (configer.openai_base_url or "https://api.openai.com/v1").rstrip("/")
        self.model: str = configer.openai_model or "gpt-3.5-turbo"
        self.timeout = 60

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set. OpenAI service will not work.")

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def generate_text(self, prompt: str) -> str:
        if not self.api_key:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OPENAI_API_KEY not set")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        try:
            data = await self._post("/chat/completions", payload)
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            # 尝试获取响应体
            try:
                body = await e.response.aread()
                logger.error(f"OpenAI HTTP error {e.response.status_code}: {body.decode()}")
            except Exception as e:
                logger.error(f"OpenAI HTTP error: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OpenAI HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"OpenAI chat completion error: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="OpenAI chat completion error, please try again")

    async def generate_chat(self, message: str, context_msg: List[Dict[str, str]]) -> str:
        if not self.api_key:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OPENAI_API_KEY not set")

        # 构建系统提示词
        messages = [{"role": "system", "content": "You are a helpful assistant."}]

        if context_msg and len(context_msg) > 0:
            messages.extend(context_msg)

        # 添加当前用户消息
        messages.append({"role": "user", "content": message})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        try:
            data = await self._post("/chat/completions", payload)
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            # 尝试获取响应体
            try:
                body = await e.response.aread()
                logger.error(f"OpenAI HTTP error {e.response.status_code}: {body.decode()}")
            except Exception as e:
                logger.error(f"OpenAI HTTP error: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OpenAI HTTP error: {e}")
        except Exception as e:
            logger.error(f"OpenAI chat completion error: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="OpenAI chat completion error, please try again")


openai_service = OpenAIService()


def get_openai_service():
    return openai_service
