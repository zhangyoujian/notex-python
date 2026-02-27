import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env 文件（使用绝对路径确保找到）
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)


def _get_env_bool(key: str, default: bool) -> bool:
    """从环境变量读取布尔值，支持 true/false、1/0 等"""
    val = os.getenv(key)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes", "on")


def _get_env_int(key: str, default: int) -> int:
    """读取整数环境变量"""
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _get_env_str(key: str, default: str) -> str:
    """读取字符串环境变量，None 时返回默认值"""
    val = os.getenv(key)
    return val if val is not None else default


@dataclass
class Config:
    # 服务器设置
    server_host: str = "0.0.0.0"
    server_port: int = 8080

    # LLM设置
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "minimax-m2.5"
    openai_vl_model: str = "gpt-4o-mini"

    # embedding模型设置
    embedding_model_name: str = "text-embedding-3-small"
    embedding_model_url: str = "http://localhost:8001/v1"

    google_api_key: Optional[str] = None

    # 向量存储设置
    vector_store_type: str = "chroma"
    vector_store_path: str = "./data/chroma_db"
    markitdown_cmd: str = "markitdown"

    # 数据库存储设置
    db_host: Optional[str] = "mysql"
    db_name: Optional[str] = "notex"
    db_user: Optional[str] = "notex_user"
    db_password: Optional[str] = "123456"
    db_port: int = 3306

    # 缓存存储设置
    redis_port: int = 6379

    # 应用设置
    max_sources: int = 5
    max_context_length: int = 128000
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # 日志设置
    log_path: str = "./logs/notex.log"
    log_level: str = "info"

    # 上传文件路径
    upload_path: str = "./data/uploads"

    # 播客生成
    enable_podcast: bool = True
    podcast_voice: str = "alloy"

    # 文档转换
    enable_markitdown: bool = True

    # 演示设置
    allow_delete: bool = True
    allow_multiple_notes_of_same_type: bool = True

    @property
    def is_ollama(self) -> bool:
        """是否使用Ollama"""
        return self.openai_base_url and "11434" in self.openai_base_url

    def supports_function_calling(self) -> bool:
        """是否支持函数调用"""
        if self.is_ollama:
            return True
        supporting_models = ["gpt-4", "gpt-3.5-turbo"]
        for model in supporting_models:
            if model in self.openai_model:
                return True
        return "gpt-4" in self.openai_model or "gpt-3.5-turbo" in self.openai_model


def load_config() -> Config:
    """从环境变量加载配置，并返回 Config 实例"""
    conf = Config()

    # 从环境变量覆盖默认值
    conf.server_host = _get_env_str("SERVER_HOST", conf.server_host)
    conf.server_port = _get_env_int("SERVER_PORT", conf.server_port)

    conf.openai_api_key = _get_env_str("OPENAI_API_KEY", conf.openai_api_key)
    conf.openai_base_url = _get_env_str("OPENAI_BASE_URL", conf.openai_base_url)
    conf.openai_model = _get_env_str("OPENAI_MODEL", conf.openai_model)
    conf.openai_vl_model = _get_env_str("OPENAI_VL_MODEL", conf.openai_vl_model)

    conf.embedding_model_name = _get_env_str("EMBEDDING_MODEL", conf.embedding_model_name)
    conf.embedding_model_url = _get_env_str("EMBEDDING_MODEL_URL", conf.embedding_model_url)

    conf.google_api_key = _get_env_str("GOOGLE_API_KEY", conf.google_api_key)


    conf.vector_store_type = _get_env_str("VECTOR_STORE_TYPE", conf.vector_store_type)
    conf.vector_store_path = _get_env_str("VECTOR_STORE_PATH", conf.vector_store_path)
    conf.markitdown_cmd = _get_env_str("MARKITDOWN_CMD", conf.markitdown_cmd)

    conf.db_name = _get_env_str("DB_NAME", conf.db_name)
    conf.db_host = _get_env_str("DB_HOST", conf.db_host)
    conf.db_user = _get_env_str("DB_USER", conf.db_user)
    conf.db_password = _get_env_str("DB_PASSWORD", conf.db_password)
    conf.db_port = _get_env_int("DB_PORT", conf.db_port)

    conf.redis_port = _get_env_int("REDIS_PORT", conf.redis_port)

    conf.max_sources = _get_env_int("MAX_SOURCES", conf.max_sources)
    conf.max_context_length = _get_env_int("MAX_CONTEXT_LENGTH", conf.max_context_length)
    conf.chunk_size = _get_env_int("CHUNK_SIZE", conf.chunk_size)
    conf.chunk_overlap = _get_env_int("CHUNK_OVERLAP", conf.chunk_overlap)

    conf.log_path = _get_env_str("LOG_PATH", conf.log_path)
    conf.log_level = _get_env_str("LOG_LEVEL", conf.log_level)

    conf.upload_path = _get_env_str("UPLOAD_PATH", conf.upload_path)

    conf.enable_podcast = _get_env_bool("ENABLE_PODCAST", conf.enable_podcast)
    conf.podcast_voice = _get_env_str("PODCAST_VOICE", conf.podcast_voice)

    conf.enable_markitdown = _get_env_bool("ENABLE_MARKITDOWN", conf.enable_markitdown)

    conf.allow_delete = _get_env_bool("ALLOW_DELETE", conf.allow_delete)
    conf.allow_multiple_notes_of_same_type = _get_env_bool(
        "ALLOW_MULTIPLE_NOTES_OF_SAME_TYPE", conf.allow_multiple_notes_of_same_type
    )

    # 验证配置
    validate_config(conf)

    return conf


def validate_config(config: Config) -> None:
    """验证配置有效性"""
    has_openai = bool(config.openai_api_key)
    has_ollama = config.is_ollama

    if not has_openai and not has_ollama:
        raise ValueError("必须设置 OPENAI_API_KEY 或 OLLAMA_BASE_URL")

    if config.vector_store_type not in ["chroma", "memory"]:
        raise ValueError(f"未知的向量存储类型: {config.vector_store_type}")


# 导出单例
configer = load_config()