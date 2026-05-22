"""持仓管理服务"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from admin.utils.db import execute_query, execute_write

class HoldingService:
    
    @staticmethod
    def get_list(page=1, page_size=20, search='', sort='updated_at', order='desc'):
        """获取持仓列表"""
        offset = (page - 1) * page_size
        where = "WHERE status = 1"
        params = []
        
        if search:
            where += " AND (code LIKE %s OR name LIKE %s)"
            params.extend([f'%{search}%', f'%{search}%'])
        
        # 排序
        allowed_sort = ['code', 'name', 'updated_at', 'profit', 'profit_pct', 'amount']
        if sort not in allowed_sort:
            sort = 'updated_at'
        order = 'DESC' if order == 'desc' else 'ASC'
        
        sql = f"SELECT * FROM holdings {where} ORDER BY {sort} {order} LIMIT %s OFFSET %s"
        params.extend([page_size, offset])
        
        items = execute_query(sql, tuple(params))
        
        # 获取总数
        count_sql = f"SELECT COUNT(*) as c FROM holdings {where}"
        total = execute_query(count_sql, tuple(params[:-2]) if params else None, one=True)['c']
        
        return items, total
    
    @staticmethod
    def get_by_id(id):
        """获取持仓详情"""
        return execute_query('SELECT * FROM holdings WHERE id = %s AND status = 1', (id,), one=True)
    
    @staticmethod
    def create(code, name, shares, cost, note=''):
        """新增持仓，自动获取NAV并计算盈亏"""
        # 检查是否已存在
        exist = execute_query('SELECT id FROM holdings WHERE code = %s AND status = 1', (code,), one=True)
        if exist:
            return None, '该基金已在持仓中'

        now = datetime.now()
        shares_f = float(shares or 0)
        cost_f = float(cost or 0)

        # 自动获取NAV和计算盈亏
        nav = 0
        amount = round(shares_f * cost_f, 2)
        profit = 0
        profit_pct = 0

        if shares_f > 0 and cost_f > 0:
            try:
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
                from core.fund_api import get_realtime_quote
                quote = get_realtime_quote(code)
                if quote and quote.get('price'):
                    nav = float(quote['price'])
                    amount = round(nav * shares_f, 2)
                    cost_total = round(cost_f * shares_f, 2)
                    profit = round(amount - cost_total, 2)
                    profit_pct = round((profit / cost_total) * 100, 2) if cost_total > 0 else 0
            except Exception:
                pass

        sql = '''INSERT INTO holdings (code, name, shares, cost, nav, amount, profit, profit_pct, note, created_at, updated_at)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
        params = (code, name, shares, cost, nav, amount, profit, profit_pct, note, now, now)

        id = execute_write(sql, params)
        return id, ''
    
    @staticmethod
    def update(id, name=None, shares=None, cost=None, note=None, alert_profit_pct=None, alert_loss_pct=None):
        """更新持仓"""
        fields = []
        params = []
        
        if name is not None:
            fields.append('name = %s')
            params.append(name)
        if shares is not None:
            fields.append('shares = %s')
            params.append(shares)
        if cost is not None:
            fields.append('cost = %s')
            params.append(cost)
        if note is not None:
            fields.append('note = %s')
            params.append(note)
        if alert_profit_pct is not None:
            fields.append('alert_profit_pct = %s')
            params.append(alert_profit_pct)
        if alert_loss_pct is not None:
            fields.append('alert_loss_pct = %s')
            params.append(alert_loss_pct)
        
        if not fields:
            return False, '没有需要更新的字段'
        
        fields.append('updated_at = %s')
        params.append(datetime.now())
        params.append(id)
        
        sql = f"UPDATE holdings SET {', '.join(fields)} WHERE id = %s AND status = 1"
        execute_write(sql, tuple(params))
        return True, ''
    
    @staticmethod
    def delete(id):
        """删除持仓（软删除）"""
        execute_write('UPDATE holdings SET status = 0, updated_at = %s WHERE id = %s', (datetime.now(), id))
        return True, ''
    
    @staticmethod
    def batch_delete(ids):
        """批量删除"""
        if not ids:
            return False, '没有选中的项'
        placeholders = ','.join(['%s'] * len(ids))
        execute_write(f'UPDATE holdings SET status = 0, updated_at = %s WHERE id IN ({placeholders})', 
                      (datetime.now(), *ids))
        return True, ''
    
    @staticmethod
    def export_csv():
        """导出CSV"""
        items = execute_query('SELECT code, name, shares, cost, note FROM holdings WHERE status = 1 ORDER BY updated_at DESC')
        return items
    
    @staticmethod
    def import_csv(rows):
        """导入CSV"""
        results = {'success': 0, 'failed': 0, 'errors': []}
        for row in rows:
            if len(row) < 4:
                continue
            code, name, shares, cost = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
            note = row[4].strip() if len(row) > 4 else ''
            
            try:
                id, msg = HoldingService.create(code, name, float(shares), float(cost), note)
                if id:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f'{code}: {msg}')
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f'{code}: {str(e)}')
        
        return results

    @staticmethod
    def refresh_all_navs():
        """刷新所有持仓的最新净值，自动计算盈亏"""
        from pathlib import Path
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from core.fund_api import get_realtime_quote
        from core.holdings import HoldingsManager

        mgr = HoldingsManager()
        holdings = mgr.list()
        updated = 0

        for h in holdings:
            code = h['code']
            shares = float(h.get('shares') or 0)
            cost = float(h.get('cost') or 0)

            if shares <= 0 or cost <= 0:
                continue

            try:
                quote = get_realtime_quote(code)
                if not quote or not quote.get('price'):
                    continue

                nav = float(quote['price'])
                amount = round(nav * shares, 2)
                cost_total = round(cost * shares, 2)
                profit = round(amount - cost_total, 2)
                profit_pct = round((profit / cost_total) * 100, 2) if cost_total > 0 else 0

                mgr.update(code, nav=nav, amount=amount, profit=profit, profit_pct=profit_pct)
                updated += 1
            except Exception:
                continue

        return {'success': True, 'count': updated}
