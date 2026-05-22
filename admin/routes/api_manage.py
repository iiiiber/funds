"""API管理路由"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Blueprint, request, session
from admin.services.api_service import APIConfigService
from admin.services.operation_log_service import OperationLogService
from admin.utils.response import success, error
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            return error('请先登录', 401)
        return f(*args, **kwargs)
    return decorated

apis_bp = Blueprint('apis', __name__)

@apis_bp.route('/', methods=['GET'])
@login_required
def list():
    """API列表页"""
    return {'template': 'api_manage.html'}

@apis_bp.route('/api/list', methods=['GET'])
@login_required
def api_list():
    """API列表API"""
    items = APIConfigService.get_list()
    for item in items:
        if item.get('api_key'):
            item['api_key'] = '******'
    return success(items)

@apis_bp.route('/api', methods=['POST'])
@login_required
def api_create():
    """新增API配置"""
    data = request.json
    id, msg = APIConfigService.create(
        name=data.get('name', ''),
        provider=data.get('provider', ''),
        api_url=data.get('api_url', ''),
        api_key=data.get('api_key', ''),
        rate_limit=int(data.get('rate_limit', 100)),
        remark=data.get('remark', '')
    )
    if not id:
        return error(msg)
    OperationLogService.log(session['admin_id'], 'api_manage', 'create', 'api_config', id, f'新增API配置 {data.get("name","")}', request.remote_addr)
    return success({'id': id}, '添加成功')

@apis_bp.route('/api/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    """更新API配置"""
    data = request.json
    ok, msg = APIConfigService.update(id,
        name=data.get('name'),
        provider=data.get('provider'),
        api_url=data.get('api_url'),
        api_key=data.get('api_key'),
        rate_limit=data.get('rate_limit'),
        remark=data.get('remark')
    )
    if not ok:
        return error(msg)
    OperationLogService.log(session['admin_id'], 'api_manage', 'update', 'api_config', id, f'更新API配置 {data.get("name","")}', request.remote_addr)
    return success(message='更新成功')

@apis_bp.route('/api/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    """删除API配置"""
    APIConfigService.delete(id)
    OperationLogService.log(session['admin_id'], 'api_manage', 'delete', 'api_config', id, f'删除API配置 {id}', request.remote_addr)
    return success(message='删除成功')

@apis_bp.route('/api/<int:id>/test', methods=['POST'])
@login_required
def api_test(id):
    """测试API连接"""
    ok, msg, duration = APIConfigService.test_connection(id)
    if not ok:
        return error(msg)
    OperationLogService.log(session['admin_id'], 'api_manage', 'test', 'api_config', id, f'测试API配置 {id}', request.remote_addr)
    return success({'duration': duration}, msg)

@apis_bp.route('/api/monitor', methods=['GET'])
@login_required
def api_monitor():
    """服务监控"""
    results = APIConfigService.monitor_all()
    OperationLogService.log(session['admin_id'], 'api_manage', 'monitor', 'api_config', None, '查看服务监控', request.remote_addr)
    return success(results)
