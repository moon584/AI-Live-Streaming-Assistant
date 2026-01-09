"""
日志配置模块
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from config import Config

def setup_logging():
    """配置日志系统"""
    # 创建 logs 目录
    if not os.path.exists(Config.LOGS_DIR):
        os.makedirs(Config.LOGS_DIR)
    
    # 设置日志格式
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件处理器 - 记录所有日志
    file_handler = RotatingFileHandler(
        os.path.join(Config.LOGS_DIR, 'app.log'),
        maxBytes=Config.LOG_MAX_BYTES,
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    
    # 错误日志文件处理器
    error_handler = RotatingFileHandler(
        os.path.join(Config.LOGS_DIR, 'error.log'),
        maxBytes=Config.LOG_MAX_BYTES,
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    # 禁用第三方库的详细日志
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return root_logger

def get_logger(name):
    """获取指定名称的logger"""
    return logging.getLogger(name)
