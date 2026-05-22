"""FundQuant 数据库模块"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Optional
from contextlib import contextmanager


class FundDB:
    """基金数据库"""
    
    def __init__(self, db_path: str = "data/fundquant.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    @contextmanager
    def _conn(self):
        """数据库连接上下文"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """初始化数据库表"""
        with self._conn() as conn:
            c = conn.cursor()
            
            # 持仓表
            c.execute('''
                CREATE TABLE IF NOT EXISTS holdings (
                    code TEXT PRIMARY KEY,
                    name TEXT,
                    shares REAL DEFAULT 0,
                    cost REAL DEFAULT 0,
                    note TEXT,
                    add_date TEXT,
                    update_date TEXT
                )
            ''')
            
            # 净值历史表
            c.execute('''
                CREATE TABLE IF NOT EXISTS nav_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT,
                    date TEXT,
                    nav REAL,
                    accum_nav REAL,
                    change_pct REAL,
                    UNIQUE(code, date)
                )
            ''')
            
            # 创建索引
            c.execute('CREATE INDEX IF NOT EXISTS idx_nav_code_date ON nav_history(code, date)')
            
            # 行情快照表
            c.execute('''
                CREATE TABLE IF NOT EXISTS quote_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT,
                    name TEXT,
                    nav REAL,
                    change_pct REAL,
                    update_time TEXT,
                    snapshot_date TEXT
                )
            ''')
            
            c.execute('CREATE INDEX IF NOT EXISTS idx_snapshot_code ON quote_snapshots(code)')
    
    # ========== 持仓操作 ==========
    
    def get_holdings(self) -> List[Dict]:
        """获取所有持仓"""
        with self._conn() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM holdings ORDER BY add_date')
            return [dict(row) for row in c.fetchall()]
    
    def add_holding(self, code: str, name: str = "", shares: float = 0,
                   cost: float = 0, note: str = "") -> bool:
        """添加持仓"""
        try:
            with self._conn() as conn:
                c = conn.cursor()
                c.execute('''
                    INSERT INTO holdings (code, name, shares, cost, note, add_date, update_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (code, name, shares, cost, note, str(date.today()), str(date.today())))
            return True
        except sqlite3.IntegrityError:
            return False
    
    def update_holding(self, code: str, **kwargs) -> bool:
        """更新持仓"""
        if not kwargs:
            return False
        
        fields = ', '.join(f"{k} = ?" for k in kwargs.keys())
        kwargs['update_date'] = str(date.today())
        fields += ', update_date = ?'
        values = list(kwargs.values()) + [code]
        
        with self._conn() as conn:
            c = conn.cursor()
            c.execute(f'UPDATE holdings SET {fields} WHERE code = ?', values)
            return c.rowcount > 0
    
    def remove_holding(self, code: str) -> bool:
        """删除持仓"""
        with self._conn() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM holdings WHERE code = ?', (code,))
            return c.rowcount > 0
    
    # ========== 净值历史操作 ==========
    
    def save_nav_history(self, code: str, records: List[Dict]):
        """保存净值历史"""
        with self._conn() as conn:
            c = conn.cursor()
            for r in records:
                c.execute('''
                    INSERT OR REPLACE INTO nav_history (code, date, nav, accum_nav, change_pct)
                    VALUES (?, ?, ?, ?, ?)
                ''', (code, r.get('date'), r.get('nav'), r.get('accum_nav'), r.get('daily_return')))
    
    def get_nav_history(self, code: str, days: int = 90) -> List[Dict]:
        """获取净值历史"""
        with self._conn() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT * FROM nav_history 
                WHERE code = ?
                ORDER BY date DESC
                LIMIT ?
            ''', (code, days))
            return [dict(row) for row in c.fetchall()]
    
    def get_nav_series(self, code: str, days: int = 90) -> List[Dict]:
        """获取净值序列（按日期升序）"""
        history = self.get_nav_history(code, days)
        return list(reversed(history))
    
    # ========== 行情快照操作 ==========
    
    def save_quote(self, code: str, name: str, nav: float, 
                   change_pct: float, update_time: str):
        """保存行情快照"""
        with self._conn() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO quote_snapshots (code, name, nav, change_pct, update_time, snapshot_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (code, name, nav, change_pct, update_time, str(date.today())))
    
    def get_latest_quotes(self) -> List[Dict]:
        """获取最新行情快照"""
        with self._conn() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT * FROM quote_snapshots q1
                WHERE snapshot_date = (
                    SELECT MAX(snapshot_date) FROM quote_snapshots q2 WHERE q2.code = q1.code
                )
            ''')
            return [dict(row) for row in c.fetchall()]
    
    # ========== 统计分析 ==========
    
    def get_performance_summary(self) -> Dict:
        """获取整体表现汇总"""
        holdings = self.get_holdings()
        
        total_cost = 0
        total_value = 0
        green_count = 0
        red_count = 0
        
        quotes = {q['code']: q for q in self.get_latest_quotes()}
        
        for h in holdings:
            q = quotes.get(h['code'], {})
            cost = h.get('cost', 0)
            shares = h.get('shares', 0)
            nav = q.get('nav', 0)
            
            if cost > 0 and shares > 0:
                cost_total = cost * shares
                value_total = nav * shares
                profit = value_total - cost_total
                
                total_cost += cost_total
                total_value += value_total
                
                if profit >= 0:
                    green_count += 1
                else:
                    red_count += 1
        
        return {
            'total_cost': total_cost,
            'total_value': total_value,
            'total_profit': total_value - total_cost,
            'profit_pct': (total_value - total_cost) / total_cost * 100 if total_cost > 0 else 0,
            'holdings_count': len(holdings),
            'green_count': green_count,
            'red_count': red_count,
        }


# 测试
if __name__ == '__main__':
    db = FundDB()
    
    print("📊 数据库测试")
    print(f"数据库路径: {db.db_path}")
    print(f"持仓数量: {len(db.get_holdings())}")
    print(f"汇总: {db.get_performance_summary()}")
