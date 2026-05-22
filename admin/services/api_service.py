"""API配置管理服务"""
import sys, requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from admin.utils.db import execute_query, execute_write
from admin.utils.encryption import encrypt_api_key, decrypt_api_key

class APIConfigService:
    
    @staticmethod
    def get_list():
        """获取API列表"""
        return execute_query('SELECT * FROM api_configs ORDER BY id ASC')
    
    @staticmethod
    def get_by_id(id):
        """获取API详情"""
        config = execute_query('SELECT * FROM api_configs WHERE id = %s', (id,), one=True)
        if config and config.get('api_key'):
            config['api_key'] = '******'
        return config
    
    @staticmethod
    def create(name, provider, api_url, api_key='', rate_limit=100, remark=''):
        """新增API配置"""
        encrypted_key = encrypt_api_key(api_key) if api_key else ''
        now = datetime.now()
        
        sql = '''INSERT INTO api_configs (name, provider, api_url, api_key, rate_limit, remark, created_at, updated_at)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s)'''
        params = (name, provider, api_url, encrypted_key, rate_limit, remark, now, now)
        
        return execute_write(sql, params), ''
    
    @staticmethod
    def update(id, **kwargs):
        """更新API配置"""
        fields = []
        params = []
        
        for k, v in kwargs.items():
            if v is not None and k != 'id':
                if k == 'api_key' and v == '******':
                    continue
                if k == 'api_key':
                    v = encrypt_api_key(v)
                fields.append(f'{k} = %s')
                params.append(v)
        
        if not fields:
            return False, '没有需要更新的字段'
        
        fields.append('updated_at = %s')
        params.append(datetime.now())
        params.append(id)
        
        sql = f"UPDATE api_configs SET {', '.join(fields)} WHERE id = %s"
        execute_write(sql, tuple(params))
        return True, ''
    
    @staticmethod
    def delete(id):
        """删除API配置"""
        execute_write('DELETE FROM api_configs WHERE id = %s', (id,))
        return True, ''
    
    @staticmethod
    def test_connection(id):
        """测试API连接"""
        config = execute_query('SELECT * FROM api_configs WHERE id = %s', (id,), one=True)
        if not config:
            return False, 'API配置不存在', 0
        
        try:
            start = datetime.now()
            resp = requests.get(config['api_url'], timeout=10)
            duration = (datetime.now() - start).total_seconds() * 1000
            
            if resp.status_code == 200:
                execute_write('UPDATE api_configs SET status = 1, last_check = %s, last_response = %s WHERE id = %s',
                             (datetime.now(), int(duration), id))
                return True, '连接正常', int(duration)
            else:
                execute_write('UPDATE api_configs SET status = 0, last_check = %s WHERE id = %s',
                             (datetime.now(), id))
                return False, f'响应错误: {resp.status_code}', 0
        except requests.exceptions.Timeout:
            execute_write('UPDATE api_configs SET status = 0, last_check = %s WHERE id = %s',
                         (datetime.now(), id))
            return False, '连接超时', 0
        except Exception as e:
            execute_write('UPDATE api_configs SET status = 0, last_check = %s WHERE id = %s',
                         (datetime.now(), id))
            return False, f'连接失败: {str(e)[:100]}', 0
    
    @staticmethod
    def monitor_all():
        """监控所有API"""
        configs = execute_query('SELECT * FROM api_configs ORDER BY id')
        results = []
        for cfg in configs:
            ok, msg, duration = APIConfigService.test_connection(cfg['id'])
            results.append({
                'id': cfg['id'],
                'name': cfg['name'],
                'provider': cfg['provider'],
                'status': '正常' if ok else '异常',
                'last_response': duration,
                'message': msg
            })
        return results
