"""操作日志服务"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from admin.utils.db import execute_query, execute_write
from datetime import datetime

class OperationLogService:
    
    # 模块常量
    MODULES = {
        'holdings': '持仓管理',
        'ai_models': 'AI模型',
        'api_manage': 'API管理',
        'settings': '系统设置',
        'feishu': '飞书推送',
        'auth': '认证',
    }
    
    # 操作常量
    ACTIONS = {
        'create': '新增',
        'update': '更新',
        'delete': '删除',
        'login': '登录',
        'logout': '登出',
        'config': '配置',
        'test': '测试',
        'import': '导入',
        'export': '导出',
    }
    
    @staticmethod
    def log(admin_id, module, action, target_type='', target_id=None, detail='', ip=''):
        """记录操作日志"""
        execute_write(
            '''INSERT INTO operation_logs (admin_id, module, action, target_type, target_id, detail, ip, created_at) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
            (admin_id, module, action, target_type, target_id, detail, ip, datetime.now())
        )
    
    @staticmethod
    def get_list(page=1, page_size=20, module=None, admin_id=None):
        """获取日志列表"""
        offset = (page - 1) * page_size
        
        where_clauses = []
        params = []
        
        if module:
            where_clauses.append('module = %s')
            params.append(module)
        
        if admin_id:
            where_clauses.append('admin_id = %s')
            params.append(admin_id)
        
        where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
        
        # 获取总数
        total = execute_query(
            f'SELECT COUNT(*) as c FROM operation_logs WHERE {where_sql}',
            tuple(params), one=True
        )['c']
        
        # 获取列表
        sql = f'''SELECT ol.*, a.username 
                  FROM operation_logs ol 
                  LEFT JOIN admins a ON ol.admin_id = a.id 
                  WHERE {where_sql}
                  ORDER BY ol.created_at DESC 
                  LIMIT %s OFFSET %s'''
        params.extend([page_size, offset])
        
        rows = execute_query(sql, tuple(params))
        
        return rows, total
    
    @staticmethod
    def get_modules():
        """获取所有模块"""
        rows = execute_query('SELECT DISTINCT module FROM operation_logs')
        return [r['module'] for r in rows]
