"""系统设置服务"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from admin.utils.db import execute_query, execute_write
import json

class SettingsService:
    
    @staticmethod
    def get(key=None):
        """获取设置"""
        if key:
            row = execute_query(
                'SELECT * FROM system_settings WHERE setting_key = %s',
                (key,), one=True
            )
            return row
        else:
            rows = execute_query('SELECT * FROM system_settings ORDER BY id')
            return rows
    
    @staticmethod
    def set(key, value, setting_type='string', remark=''):
        """设置值"""
        sql = '''INSERT INTO system_settings (setting_key, setting_value, setting_type, remark) 
                 VALUES (%s, %s, %s, %s)
                 ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value), setting_type=VALUES(setting_type), remark=VALUES(remark)'''
        execute_write(sql, (key, value, setting_type, remark))
        return True
    
    @staticmethod
    def get_value(key, default=None):
        """获取值（简化）"""
        row = execute_query(
            'SELECT setting_value FROM system_settings WHERE setting_key = %s',
            (key,), one=True
        )
        if row:
            return row['setting_value']
        return default
    
    @staticmethod
    def delete(key):
        """删除设置"""
        execute_write('DELETE FROM system_settings WHERE setting_key = %s', (key,))
        return True
