"""AI模型管理器 - 从数据库读取配置"""
import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, List
import pymysql
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'funds',
    'password': '6NZ7Hp2Z5YWShARJ',
    'database': 'funds',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

@contextmanager
def get_db():
    """数据库连接上下文"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


class AIModelManager:
    """AI模型管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._cache = None
        self._cache_time = 0
    
    def _get_default_model(self) -> Optional[Dict]:
        """从数据库获取默认模型"""
        try:
            with get_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        'SELECT * FROM ai_models WHERE is_default = 1 AND status = 1 LIMIT 1'
                    )
                    return cursor.fetchone()
        except Exception as e:
            logger.error(f"获取默认AI模型失败: {e}")
            return None
    
    def _decrypt_api_key(self, encrypted_key: str) -> str:
        """解密API密钥"""
        if not encrypted_key:
            return ''
        try:
            import base64
            import hashlib
            from cryptography.fernet import Fernet
            
            _key = base64.urlsafe_b64encode(hashlib.sha256(b'fundquant_admin_key_2026').digest())
            fernet = Fernet(_key)
            return fernet.decrypt(encrypted_key.encode()).decode()
        except:
            return ''
    
    def get_default_model(self) -> Optional[Dict]:
        """获取默认模型配置（带缓存）"""
        import time
        now = time.time()
        
        # 缓存5分钟
        if self._cache and (now - self._cache_time) < 300:
            return self._cache
        
        model = self._get_default_model()
        if model:
            # 解密API密钥
            if model.get('api_key'):
                model['api_key'] = self._decrypt_api_key(model['api_key'])
            self._cache = model
            self._cache_time = now
        
        return model
    
    def get_model_by_id(self, model_id: int) -> Optional[Dict]:
        """根据ID获取模型"""
        try:
            with get_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT * FROM ai_models WHERE id = %s AND status = 1', (model_id,))
                    model = cursor.fetchone()
                    if model and model.get('api_key'):
                        model['api_key'] = self._decrypt_api_key(model['api_key'])
                    return model
        except Exception as e:
            logger.error(f"获取AI模型失败: {e}")
            return None
    
    def list_models(self) -> List[Dict]:
        """列出所有模型"""
        try:
            with get_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT * FROM ai_models WHERE status = 1 ORDER BY is_default DESC, id ASC')
                    models = cursor.fetchall()
                    for m in models:
                        if m.get('api_key'):
                            m['api_key'] = '******'  # 脱敏
                    return models
        except Exception as e:
            logger.error(f"列出AI模型失败: {e}")
            return []
    
    def init_default_from_env(self):
        """如果数据库没有模型，从环境变量初始化"""
        env_key = os.environ.get('MINIMAX_API_KEY', '')
        if not env_key or env_key == '***':
            # 尝试读取.env文件
            env_file = Path(__file__).parent.parent / '.env'
            if env_file.exists():
                with open(env_file) as f:
                    for line in f:
                        if line.strip().startswith('MINIMAX_API_KEY='):
                            env_key = line.split('=', 1)[1].strip()
                            break
        
        if not env_key or env_key == '***':
            logger.warning("未找到MINIMAX_API_KEY")
            return
        
        # 检查是否已有模型
        existing = self._get_default_model()
        if existing:
            logger.info("数据库已有AI模型配置，跳过初始化")
            return
        
        logger.info("初始化默认AI模型...")
        
        # 加密并保存
        import base64
        import hashlib
        from cryptography.fernet import Fernet
        
        _key = base64.urlsafe_b64encode(hashlib.sha256(b'fundquant_admin_key_2026').digest())
        fernet = Fernet(_key)
        encrypted_key = fernet.encrypt(env_key.encode()).decode()
        
        try:
            with get_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO ai_models (name, type, api_url, api_key, model_id, timeout, temperature, max_tokens, is_default, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ''', (
                        'MiniMax v2 (环境变量初始化)',
                        'chat',
                        'https://api.minimaxi.com/anthropic/v1/messages',
                        encrypted_key,
                        'MiniMax-M2.7-highspeed',
                        30, 0.5, 300, 1, 1
                    ))
            logger.info("AI模型初始化成功")
        except Exception as e:
            logger.error(f"AI模型初始化失败: {e}")


# 全局单例
ai_model_manager = AIModelManager()


if __name__ == '__main__':
    # 测试
    manager = AIModelManager()
    
    # 初始化（如果需要）
    manager.init_default_from_env()
    
    # 获取默认模型
    model = manager.get_default_model()
    if model:
        print(f"默认模型: {model['name']}")
        print(f"API地址: {model['api_url']}")
        print(f"模型ID: {model['model_id']}")
    else:
        print("未找到默认AI模型配置")
