"""操作日志路由"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Blueprint, request, session
from admin.services.operation_log_service import OperationLogService
from admin.utils.response import success, error, page_data
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            return error('请先登录', 401)
        return f(*args, **kwargs)
    return decorated

logs_bp = Blueprint('logs', __name__)

@logs_bp.route('/logs', methods=['GET'])
@login_required
def list():
    """日志列表页"""
    return {'template': 'operation_logs.html'}

@logs_bp.route('/logs/operation/list', methods=['GET'])
@login_required
def api_list():
    """获取操作日志列表"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    module = request.args.get('module')
    admin_id = request.args.get('admin_id')
    
    if admin_id:
        admin_id = int(admin_id)
    
    items, total = OperationLogService.get_list(page, page_size, module, admin_id)
    return success(page_data(items, total, page, page_size))

@logs_bp.route('/logs/operation/modules', methods=['GET'])
@login_required
def api_modules():
    """获取所有模块"""
    modules = OperationLogService.get_modules()
    return success(modules)

@logs_bp.route('/logs/operation/stats', methods=['GET'])
@login_required
def api_stats():
    """获取操作统计"""
    from admin.utils.db import execute_query
    
    # 各模块操作次数
    stats = execute_query('''
        SELECT module, action, COUNT(*) as cnt 
        FROM operation_logs 
        GROUP BY module, action 
        ORDER BY cnt DESC
    ''')
    
    return success(stats)
