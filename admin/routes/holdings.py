"""持仓管理路由"""
import sys, csv, io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Blueprint, request, session
from admin.services.holding_service import HoldingService
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

holdings_bp = Blueprint('holdings', __name__)

@holdings_bp.route('/', methods=['GET'])
@login_required
def list():
    """持仓列表页"""
    return {'template': 'holdings.html'}

@holdings_bp.route('/api/list', methods=['GET'])
@login_required
def api_list():
    """持仓列表API"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'updated_at')
    order = request.args.get('order', 'desc')
    
    items, total = HoldingService.get_list(page, page_size, search, sort, order)
    return success(page_data(items, total, page, page_size))

@holdings_bp.route('/api', methods=['POST'])
@login_required
def api_create():
    """新增持仓"""
    data = request.json
    code = data.get('code', '').strip()
    name = data.get('name', '').strip()
    shares = data.get('shares', 0)
    cost = data.get('cost', 0)
    note = data.get('note', '')
    
    if not code:
        return error('请输入基金代码')
    
    id, msg = HoldingService.create(code, name, shares, cost, note)
    if not id:
        return error(msg)
    
    OperationLogService.log(session['admin_id'], 'holdings', 'create', 'holding', id, f'新增基金 {code} {name}', request.remote_addr)
    return success({'id': id}, '添加成功')

@holdings_bp.route('/api/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    """更新持仓"""
    data = request.json
    ok, msg = HoldingService.update(id, 
        name=data.get('name'),
        shares=data.get('shares'),
        cost=data.get('cost'),
        note=data.get('note'),
        alert_profit_pct=data.get('alert_profit_pct'),
        alert_loss_pct=data.get('alert_loss_pct')
    )
    if not ok:
        return error(msg)
    OperationLogService.log(session['admin_id'], 'holdings', 'update', 'holding', id, f'更新持仓 {id}', request.remote_addr)
    return success(message='更新成功')

@holdings_bp.route('/api/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    """删除持仓"""
    HoldingService.delete(id)
    OperationLogService.log(session['admin_id'], 'holdings', 'delete', 'holding', id, f'删除持仓 {id}', request.remote_addr)
    return success(message='删除成功')

@holdings_bp.route('/api/batch-delete', methods=['POST'])
@login_required
def api_batch_delete():
    """批量删除"""
    ids = request.json.get('ids', [])
    HoldingService.batch_delete(ids)
    OperationLogService.log(session['admin_id'], 'holdings', 'delete', 'holding', None, f'批量删除 {len(ids)} 条持仓', request.remote_addr)
    return success(message='批量删除成功')

@holdings_bp.route('/api/export', methods=['GET'])
@login_required
def api_export():
    """导出CSV"""
    items = HoldingService.export_csv()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['基金代码', '基金名称', '持有份额', '买入成本', '备注'])
    for item in items:
        writer.writerow([item['code'], item['name'], item['shares'], item['cost'], item.get('note', '')])
    
    OperationLogService.log(session['admin_id'], 'holdings', 'export', 'holding', None, '导出持仓CSV', request.remote_addr)
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=holdings.csv'
    }

@holdings_bp.route('/api/import', methods=['POST'])
@login_required
def api_import():
    """导入CSV"""
    file = request.files.get('file')
    if not file:
        return error('请选择文件')
    
    stream = io.StringIO(file.stream.read().decode('utf-8'))
    reader = csv.reader(stream)
    next(reader, None)  # 跳过表头
    
    rows = list(reader)
    results = HoldingService.import_csv(rows)
    OperationLogService.log(session['admin_id'], 'holdings', 'import', 'holding', None, f'导入 {results.get("success",0)} 条持仓', request.remote_addr)
    return success(results, '导入完成')

@holdings_bp.route('/api/refresh-navs', methods=['POST'])
@login_required
def api_refresh_navs():
    """刷新所有持仓的最新净值和盈亏"""
    from admin.services.holding_service import HoldingService
    result = HoldingService.refresh_all_navs()
    if result['success']:
        OperationLogService.log(session['admin_id'], 'holdings', 'refresh', 'holding', None, f'刷新 {result["count"]} 只基金净值', request.remote_addr)
    return success(result, f'刷新了 {result["count"]} 只基金')
