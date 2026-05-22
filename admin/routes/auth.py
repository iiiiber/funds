"""认证路由"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Blueprint, request, session, redirect, url_for
from admin.services.auth_service import AuthService
from admin.services.operation_log_service import OperationLogService
from admin.utils.response import success, error

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'GET':
        return {'template': 'login.html'}
    
    data = request.json or request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return error('请输入用户名和密码')
    
    ip = request.remote_addr or ''
    user_agent = request.headers.get('User-Agent', '')[:500]
    
    admin, msg = AuthService.login(username, password, ip, user_agent)
    
    if not admin:
        OperationLogService.log(None, 'auth', 'login_fail', 'admin', None, f'登录失败: {username}', ip)
        return error(msg or '登录失败')
    
    # 设置session
    session['admin_id'] = admin['id']
    session['admin_name'] = admin['username']
    session['real_name'] = admin.get('real_name', '')
    
    OperationLogService.log(admin['id'], 'auth', 'login', 'admin', admin['id'], f'管理员 {username} 登录', ip)
    return success({'redirect': '/admin/'}, '登录成功')

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """登出"""
    admin_id = session.get('admin_id')
    admin_name = session.get('admin_name', '')
    session.clear()
    OperationLogService.log(admin_id, 'auth', 'logout', 'admin', admin_id, f'管理员 {admin_name} 登出', request.remote_addr or '')
    return success(message='已退出登录')

@auth_bp.route('/password', methods=['POST'])
def change_password():
    """修改密码"""
    if 'admin_id' not in session:
        return error('请先登录', 401)
    
    data = request.json
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    if not old_password or not new_password:
        return error('请填写完整')
    
    if len(new_password) < 6:
        return error('新密码至少6位')
    
    ok, msg = AuthService.change_password(session['admin_id'], old_password, new_password)
    
    if not ok:
        return error(msg)
    
    OperationLogService.log(session['admin_id'], 'auth', 'update', 'admin', session['admin_id'], '修改密码', request.remote_addr or '')
    return success(message='密码修改成功')

@auth_bp.route('/info', methods=['GET'])
def info():
    """当前用户信息"""
    if 'admin_id' not in session:
        return error('未登录', 401)
    
    admin = AuthService.get_admin_by_id(session['admin_id'])
    if not admin:
        session.clear()
        return error('用户不存在', 401)
    
    return success(admin)
