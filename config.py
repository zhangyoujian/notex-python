import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config(BaseSettings):
    """配置类"""

    # 服务器设置
    server_host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    server_port: int = Field(default=8080, env="SERVER_PORT")

    # LLM设置
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_base_url: Optional[str] = Field(default=None, env="OPENAI_BASE_URL")
    openai_model: Optional[str] = Field(default="Qwen3-32B", env="OPENAI_MODE")
    openai_vl_model: Optional[str] = Field(default="gpt-4o-mini", env="OPENAI_VL_MODEL")

    # embedding模型设置
    embedding_model: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")

    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")

    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", env="OLLAMA_MODEL")

    # 向量存储设置
    vector_store_type: str = Field(default="chroma", env="VECTOR_STORE_TYPE")

    # 数据库存储设置
    mysql_url: Optional[str] = Field(default=None, env="MYSQL_URL")

    # 缓存存储设置
    redis_url: str = Field(default=None, env="REDIS_URL")

    # 应用设置
    max_sources: int = Field(default=5, env="MAX_SOURCES")
    max_context_length: int = Field(default=128000, env="MAX_CONTEXT_LENGTH")
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")

    # 日志设置
    log_path: str = Field(default="./logs/notex.log", env="LOG_PATH")
    log_level: str = Field(default="info", env="LOG_LEVEL")

    # 上传文件路径
    upload_path: str = Field(default="./data/uploads", env="UPLOAD_PATH")

    # AES 加密算法依赖的秘钥
    aes_key: str = Field(default=None, env="AES_KEY")

    # 播客生成
    enable_podcast: bool = Field(default=True, env="ENABLE_PODCAST")
    podcast_voice: str = Field(default="alloy", env="PODCAST_VOICE")

    # 文档转换
    enable_markitdown: bool = Field(default=True, env="ENABLE_MARKITDOWN")

    # 演示设置
    allow_delete: bool = Field(default=True, env="ALLOW_DELETE")
    allow_multiple_notes_of_same_type: bool = Field(default=True, env="ALLOW_MULTIPLE_NOTES_OF_SAME_TYPE")

    # LangSmith跟踪（可选）
    langchain_api_key: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="open-notebook", env="LANGCHAIN_PROJECT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @field_validator("openai_base_url")
    def set_openai_base_url(cls, v, values):
        """自动检测提供者"""
        if v is None and "openai_model" in values:
            model = values.get("openai_model", "")
            if "ollama" in model.lower() or "llama" in model.lower():
                return values.get("ollama_base_url", "http://localhost:11434")
        return v

    @property
    def is_ollama(self) -> bool:
        """是否使用Ollama"""
        return self.openai_base_url and "11434" in self.openai_base_url

    def supports_function_calling(self) -> bool:
        """是否支持函数调用"""
        if self.is_ollama:
            return True  # 大多数Ollama模型现在支持工具调用

        # OpenAI支持函数调用的模型
        supporting_models = ["gpt-4", "gpt-3.5-turbo"]
        for model in supporting_models:
            if model in self.openai_model:
                return True
        return "gpt-4" in self.openai_model or "gpt-3.5-turbo" in self.openai_model


def validate_config(config: Config) -> None:
    """验证配置"""
    has_openai = bool(config.openai_api_key)
    has_ollama = config.is_ollama

    if not has_openai and not has_ollama:
        raise ValueError("必须设置 OPENAI_API_KEY 或 OLLAMA_BASE_URL")

    # 验证向量存储配置
    if config.vector_store_type == "supabase":
        if not config.supabase_url or not config.supabase_key:
            raise ValueError("SUPABASE_URL 和 SUPABASE_KEY 对于supabase向量存储是必需的")
    elif config.vector_store_type not in ["chroma", "memory"]:
        raise ValueError(f"未知的向量存储类型: {config.vector_store_type}")


def load_config() -> Config:
    """加载配置"""
    conf_ = Config()

    # 验证配置
    validate_config(conf_)

    return conf_


configer = load_config()

