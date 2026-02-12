from utils.logger_manager import LoggerFactory
from config import configer
import logging


LOGGING_TYPE = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARN,
    "error": logging.ERROR
}

logger = LoggerFactory.get_logger("notex", configer.log_path, LOGGING_TYPE[configer.log_level])
