"""飞书推送管理路由"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Blueprint, jsonify, request, session, render_template
from ..utils.db import execute_query, execute_write
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

feishu_bp = Blueprint('feishu', __name__)

@feishu_bp.route('/feishu')
@login_required
def index():
    """飞书推送配置页面"""
    return render_template('feishu.html')

@feishu_bp.route('/settings', methods=['GET'])
@login_required
def get_settings():
    """获取飞书推送设置"""
    try:
        rows = execute_query('SELECT * FROM feishu_settings WHERE id = 1')
        if rows:
            return jsonify({'success': True, 'data': rows[0]})
        return jsonify({'success': False, 'message': '未找到配置'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@feishu_bp.route('/settings', methods=['POST'])
@login_required
def save_settings():
    """保存飞书推送设置"""
    try:
        data = request.get_json()
        webhook_url = data.get('webhook_url', '').strip()
        enabled = 1 if data.get('enabled') else 0
        push_condition = data.get('push_condition', 'all')
        
        sql = '''INSERT INTO feishu_settings (id, webhook_url, enabled, push_condition) 
                  VALUES (1, %s, %s, %s)
                  ON DUPLICATE KEY UPDATE webhook_url=VALUES(webhook_url), enabled=VALUES(enabled), push_condition=VALUES(push_condition)'''
        execute_write(sql, (webhook_url, enabled, push_condition))
        OperationLogService.log(session.get('admin_id'), 'feishu', 'config', 'feishu_setting', 1, f'配置飞书推送 enabled={enabled}', request.remote_addr or '')
        return jsonify({'success': True, 'message': '保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@feishu_bp.route('/test', methods=['POST'])
@login_required
def test_push():
    """测试飞书推送"""
    import requests
    try:
        settings = execute_query('SELECT * FROM feishu_settings WHERE id = 1')
        if not settings or not settings[0]['webhook_url']:
            return jsonify({'success': False, 'message': '请先配置WebHook地址'})
        
        webhook_url = settings[0]['webhook_url']
        
        test_data = {
            'msg_type': 'text',
            'content': {'text': '🔔 FundQuant 飞书推送测试成功！\n这是一条来自基金量化助手的测试消息。'}
        }
        
        resp = requests.post(webhook_url, json=test_data, timeout=10)
        result = resp.json()
        
        if resp.status_code == 200 and (result.get('code') == 0 or result.get('StatusCode') == 0):
            OperationLogService.log(session.get('admin_id'), 'feishu', 'test', 'feishu_setting', 1, '测试飞书推送', request.remote_addr or '')
            return jsonify({'success': True, 'message': '推送成功！'})
        else:
            return jsonify({'success': False, 'message': f"推送失败: {result}"})
    except Exception as e:
        return jsonify({'success': False, 'message': f"测试失败: {str(e)}"})
