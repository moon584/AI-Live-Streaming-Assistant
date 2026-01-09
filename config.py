"""
配置管理模块
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """应用配置"""
    # Flask配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # 数据库配置
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'live_assistant')
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
    
    # AI配置
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/chat/completions')
    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    
    # 缓存配置
    QA_CACHE_MAX_SIZE = int(os.getenv('QA_CACHE_MAX_SIZE', '1000'))
    
    # 文件路径
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    
    BLACKLIST_FILE = os.path.join(DATA_DIR, 'blacklist.json')
    WHITELIST_FILE = os.path.join(DATA_DIR, 'whitelist.json')
    IRRELEVANT_BLACKLIST_FILE = os.path.join(DATA_DIR, 'irrelevant_blacklist.json')
    IRRELEVANT_COUNTS_FILE = os.path.join(DATA_DIR, 'irrelevant_counts.json')
    
    # 日志配置
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
