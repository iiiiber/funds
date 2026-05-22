"""系统设置路由"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Blueprint, request, session
from admin.services.settings_service import SettingsService
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

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET'])
@login_required
def list():
    """设置列表页"""
    return {'template': 'settings.html'}

@settings_bp.route('/settings/list', methods=['GET'])
@login_required
def api_list():
    """获取所有设置"""
    items = SettingsService.get()
    return success(items)

@settings_bp.route('/settings/item/<key>', methods=['GET'])
@login_required
def api_get(key):
    """获取单个设置"""
    item = SettingsService.get(key)
    if not item:
        return error('设置不存在')
    return success(item)

@settings_bp.route('/settings', methods=['POST'])
@login_required
def api_set():
    """新增/更新设置"""
    data = request.json
    key = data.get('key', '').strip()
    value = data.get('value', '')
    setting_type = data.get('type', 'string')
    remark = data.get('remark', '')
    
    if not key:
        return error('设置键不能为空')
    
    SettingsService.set(key, value, setting_type, remark)
    
    # 记录操作日志
    OperationLogService.log(
        admin_id=session.get('admin_id'),
        module='settings',
        action='config',
        target_type='system_setting',
        detail=f'设置 {key} = {value}',
        ip=request.remote_addr or ''
    )
    
    return success(message='保存成功')

@settings_bp.route('/settings/item/<key>', methods=['PUT'])
@login_required
def api_update(key):
    """更新设置"""
    data = request.json
    value = data.get('value', '')
    setting_type = data.get('type')
    remark = data.get('remark')
    
    item = SettingsService.get(key)
    if not item:
        return error('设置不存在')
    
    SettingsService.set(key, value, setting_type or item.get('setting_type', 'string'), remark or item.get('remark', ''))
    
    # 记录操作日志
    OperationLogService.log(
        admin_id=session.get('admin_id'),
        module='settings',
        action='update',
        target_type='system_setting',
        detail=f'更新设置 {key} = {value}',
        ip=request.remote_addr or ''
    )
    
    return success(message='更新成功')

@settings_bp.route('/settings/item/<key>', methods=['DELETE'])
@login_required
def api_delete(key):
    """删除设置"""
    SettingsService.delete(key)
    
    # 记录操作日志
    OperationLogService.log(
        admin_id=session.get('admin_id'),
        module='settings',
        action='delete',
        target_type='system_setting',
        detail=f'删除设置 {key}',
        ip=request.remote_addr or ''
    )
    
    return success(message='删除成功')

@settings_bp.route('/settings/batch', methods=['POST'])
@login_required
def api_batch_set():
    """批量保存设置"""
    data = request.json
    settings = data.get('settings', [])
    
    for item in settings:
        key = item.get('key', '').strip()
        value = item.get('value', '')
        if key:
            SettingsService.set(key, value, item.get('type', 'string'), item.get('remark', ''))
    
    # 记录操作日志
    OperationLogService.log(
        admin_id=session.get('admin_id'),
        module='settings',
        action='config',
        target_type='system_setting',
        detail=f'批量更新 {len(settings)} 项设置',
        ip=request.remote_addr or ''
    )
    
    return success(message='批量保存成功')
