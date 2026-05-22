"""AI模型管理路由"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Blueprint, request, session
from admin.services.ai_service import AIService
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

models_bp = Blueprint('models', __name__)

@models_bp.route('/', methods=['GET'])
@login_required
def list():
    """模型列表页"""
    return {'template': 'ai_models.html'}

@models_bp.route('/api/list', methods=['GET'])
@login_required
def api_list():
    """模型列表API"""
    items = AIService.get_list()
    # 脱敏API密钥
    for item in items:
        if item.get('api_key'):
            item['api_key'] = '******'
    return success(items)

@models_bp.route('/api', methods=['POST'])
@login_required
def api_create():
    """新增模型"""
    data = request.json
    id, msg = AIService.create(
        name=data.get('name', ''),
        type=data.get('type', 'chat'),
        api_url=data.get('api_url', ''),
        api_key=data.get('api_key', ''),
        model_id=data.get('model_id', ''),
        timeout=int(data.get('timeout', 30)),
        temperature=float(data.get('temperature', 0.5)),
        max_tokens=int(data.get('max_tokens', 300)),
        remark=data.get('remark', '')
    )
    if not id:
        return error(msg)
    OperationLogService.log(session['admin_id'], 'ai_models', 'create', 'ai_model', id, f'新增AI模型 {data.get("name","")}', request.remote_addr)
    return success({'id': id}, '添加成功')

@models_bp.route('/api/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    """更新模型"""
    data = request.json
    ok, msg = AIService.update(id,
        name=data.get('name'),
        type=data.get('type'),
        api_url=data.get('api_url'),
        api_key=data.get('api_key'),
        model_id=data.get('model_id'),
        timeout=data.get('timeout'),
        temperature=data.get('temperature'),
        max_tokens=data.get('max_tokens'),
        remark=data.get('remark')
    )
    if not ok:
        return error(msg)
    OperationLogService.log(session['admin_id'], 'ai_models', 'update', 'ai_model', id, f'更新AI模型 {data.get("name","")}', request.remote_addr)
    return success(message='更新成功')

@models_bp.route('/api/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    """删除模型"""
    AIService.delete(id)
    OperationLogService.log(session['admin_id'], 'ai_models', 'delete', 'ai_model', id, f'删除AI模型 {id}', request.remote_addr)
    return success(message='删除成功')

@models_bp.route('/api/<int:id>/test', methods=['POST'])
@login_required
def api_test(id):
    """测试连接"""
    ok, msg = AIService.test_connection(id)
    if not ok:
        return error(msg)
    OperationLogService.log(session['admin_id'], 'ai_models', 'test', 'ai_model', id, f'测试AI模型 {id} 连接', request.remote_addr)
    return success(message=msg)

@models_bp.route('/api/<int:id>/default', methods=['POST'])
@login_required
def api_set_default(id):
    """设为默认"""
    AIService.set_default(id)
    OperationLogService.log(session['admin_id'], 'ai_models', 'config', 'ai_model', id, f'设置AI模型 {id} 为默认', request.remote_addr)
    return success(message='设置成功')
