"""
通用工具函数
"""
import re
import hashlib
import json
import os
from utils.logger import get_logger

logger = get_logger(__name__)

def normalize_question(question):
    """
    问题归一化：去除标点符号和语气词
    用于提高缓存命中率
    """
    if not question:
        return ""
    
    # 去除标点符号
    normalized = re.sub(r'[？?！!。.，,、；;：:""\'\'""（）()【】\[\]]', '', question)
    
    # 去除语气词
    normalized = re.sub(r'(吗|呢|啊|哦|嘛|呀|哇|哈)+', '', normalized)
    
    # 统一"么"为"吗"
    normalized = normalized.replace('么', '吗')
    
    # 转小写并去除多余空格
    normalized = normalized.lower().strip()
    
    return normalized

def calculate_hash(text):
    """计算文本的SHA256哈希值"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def load_json_file(path):
    """加载JSON文件"""
    try:
        if not os.path.exists(path):
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"无法加载 JSON 文件 {path}: {e}")
        return {}

def save_json_file(path, data):
    """保存JSON文件"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"无法保存 JSON 文件 {path}: {e}")
        return False

def validate_uuid(uuid_string):
    """验证UUID格式"""
    import uuid
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False
