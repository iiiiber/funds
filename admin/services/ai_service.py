"""AI模型服务"""
import sys, requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from admin.utils.db import execute_query, execute_write
from admin.utils.encryption import encrypt_api_key, decrypt_api_key

class AIService:
    
    @staticmethod
    def get_list():
        """获取模型列表"""
        return execute_query('SELECT * FROM ai_models ORDER BY is_default DESC, id ASC')
    
    @staticmethod
    def get_by_id(id):
        """获取模型详情"""
        model = execute_query('SELECT * FROM ai_models WHERE id = %s', (id,), one=True)
        if model and model.get('api_key'):
            model['api_key'] = '******'  # 脱敏
        return model
    
    @staticmethod
    def create(name, type, api_url, api_key, model_id, timeout=30, temperature=0.5, max_tokens=300, remark=''):
        """新增模型"""
        encrypted_key = encrypt_api_key(api_key) if api_key else ''
        now = datetime.now()
        
        sql = '''INSERT INTO ai_models (name, type, api_url, api_key, model_id, timeout, temperature, max_tokens, remark, created_at, updated_at)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
        params = (name, type, api_url, encrypted_key, model_id, timeout, temperature, max_tokens, remark, now, now)
        
        id = execute_write(sql, params)
        
        # 如果是第一个，设为默认
        count = execute_query('SELECT COUNT(*) as c FROM ai_models', one=True)['c']
        if count == 1:
            execute_write('UPDATE ai_models SET is_default = 1 WHERE id = %s', (id,))
        
        return id, ''
    
    @staticmethod
    def update(id, **kwargs):
        """更新模型"""
        fields = []
        params = []
        
        for k, v in kwargs.items():
            if v is not None and k != 'id':
                if k == 'api_key' and v and v != '******':
                    v = encrypt_api_key(v)
                elif k == 'api_key' and v == '******':
                    continue
                fields.append(f'{k} = %s')
                params.append(v)
        
        if not fields:
            return False, '没有需要更新的字段'
        
        fields.append('updated_at = %s')
        params.append(datetime.now())
        params.append(id)
        
        sql = f"UPDATE ai_models SET {', '.join(fields)} WHERE id = %s"
        execute_write(sql, tuple(params))
        return True, ''
    
    @staticmethod
    def delete(id):
        """删除模型"""
        execute_write('DELETE FROM ai_models WHERE id = %s', (id,))
        return True, ''
    
    @staticmethod
    def set_default(id):
        """设为默认模型"""
        execute_write('UPDATE ai_models SET is_default = 0')  # 取消所有默认
        execute_write('UPDATE ai_models SET is_default = 1 WHERE id = %s', (id,))
        return True, ''
    
    @staticmethod
    def test_connection(id):
        """测试连接"""
        model = execute_query('SELECT * FROM ai_models WHERE id = %s', (id,), one=True)
        if not model:
            return False, '模型不存在'
        
        api_key = decrypt_api_key(model.get('api_key', ''))
        if not api_key:
            return False, 'API密钥未配置'
        
        try:
            resp = requests.post(
                model['api_url'],
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': model['model_id'],
                    'messages': [{'role': 'user', 'content': 'Hi'}],
                    'max_tokens': 10
                },
                timeout=model.get('timeout', 30)
            )
            
            if resp.status_code == 200:
                return True, '连接成功'
            else:
                return False, f'响应错误: {resp.status_code}'
        except requests.exceptions.Timeout:
            return False, '连接超时'
        except Exception as e:
            return False, f'连接失败: {str(e)[:100]}'
