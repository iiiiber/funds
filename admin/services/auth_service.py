"""认证服务"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from admin.utils.db import execute_query, execute_write
from admin.utils.encryption import hash_password, verify_password, generate_salt

class AuthService:
    
    @staticmethod
    def login(username, password, ip='', user_agent=''):
        """登录"""
        # 获取管理员
        admin = execute_query(
            'SELECT * FROM admins WHERE username = %s AND status = 1',
            (username,), one=True
        )
        
        if not admin:
            return None, '用户名或密码错误'
        
        # 验证密码
        if not verify_password(password, admin['salt'], admin['password']):
            # 记录失败日志
            AuthService._log_login(admin['id'], username, ip, user_agent, 'failed', '密码错误')
            return None, '用户名或密码错误'
        
        # 更新最后登录时间
        execute_write(
            'UPDATE admins SET last_login = %s WHERE id = %s',
            (datetime.now(), admin['id'])
        )
        
        # 记录成功日志
        AuthService._log_login(admin['id'], username, ip, user_agent, 'success')
        
        # 返回管理员信息（不含密码）
        admin.pop('password', None)
        admin.pop('salt', None)
        return admin, ''
    
    @staticmethod
    def _log_login(admin_id, username, ip, user_agent, status, fail_reason=''):
        """记录登录日志"""
        execute_write(
            '''INSERT INTO login_logs (admin_id, username, ip, user_agent, status, fail_reason) 
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (admin_id, username, ip, user_agent, status, fail_reason)
        )
    
    @staticmethod
    def change_password(admin_id, old_password, new_password):
        """修改密码"""
        admin = execute_query(
            'SELECT * FROM admins WHERE id = %s',
            (admin_id,), one=True
        )
        
        if not admin:
            return False, '管理员不存在'
        
        if not verify_password(old_password, admin['salt'], admin['password']):
            return False, '原密码错误'
        
        new_salt = generate_salt()
        new_hash = hash_password(new_password, new_salt)
        
        execute_write(
            'UPDATE admins SET password = %s, salt = %s WHERE id = %s',
            (new_hash, new_salt, admin_id)
        )
        
        return True, ''
    
    @staticmethod
    def get_admin_by_id(admin_id):
        """获取管理员信息"""
        admin = execute_query(
            'SELECT id, username, real_name, email, status, last_login FROM admins WHERE id = %s',
            (admin_id,), one=True
        )
        return admin
    
    @staticmethod
    def get_login_logs(page=1, page_size=20):
        """获取登录日志"""
        offset = (page - 1) * page_size
        logs = execute_query(
            '''SELECT * FROM login_logs ORDER BY login_time DESC LIMIT %s OFFSET %s''',
            (page_size, offset)
        )
        total = execute_query('SELECT COUNT(*) as c FROM login_logs', one=True)['c']
        return logs, total
