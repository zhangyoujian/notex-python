import logging
import os.path
from logging.handlers import RotatingFileHandler


class LoggerFactory:
    logger_handler = {}

    @staticmethod
    def init(name, logfile_path, log_level):

        log_dir = os.path.dirname(logfile_path)
        if not os.path.isdir(log_dir):
            os.mkdir(log_dir)

        logger = logging.getLogger(name)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(process)d - %(message)s')
        # 添加文件句柄
        file_handler = RotatingFileHandler(logfile_path, maxBytes=5*1024*1024, backupCount=5)
        file_handler.setFormatter(formatter)

        # # 添加控制台句柄
        std_handler = logging.StreamHandler()
        std_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(std_handler)

        logger.setLevel(log_level)

        return logger

    @staticmethod
    def get_logger(name, log_path=None, log_level=logging.DEBUG):
        if name in LoggerFactory.logger_handler:
            return LoggerFactory.logger_handler[name]

        LoggerFactory.logger_handler[name] = LoggerFactory.init(name, log_path, log_level)

        return LoggerFactory.logger_handler[name]
