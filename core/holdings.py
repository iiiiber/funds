"""基金持仓管理 - 使用MySQL数据库"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from datetime import datetime
import pymysql
from pymysql.cursors import DictCursor
from typing import List, Dict, Optional

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'funds',
    'password': '6NZ7Hp2Z5YWShARJ',
    'database': 'funds',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

class HoldingsManager:
    def _get_conn(self):
        return pymysql.connect(**DB_CONFIG)
    
    def list(self) -> List[Dict]:
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, code, name, shares, cost, note, "
                    "nav, amount, profit, profit_pct, created_at, updated_at "
                    "FROM holdings WHERE status = 1 ORDER BY updated_at DESC"
                )
                results = cursor.fetchall()
                # 转换数值类型
                for h in results:
                    for field in ['shares', 'cost', 'nav', 'amount', 'profit', 'profit_pct']:
                        if field in h and h[field] is not None:
                            h[field] = float(h[field])
                return results
        finally:
            conn.close()
    
    def add(self, code: str, name: str = '', shares: float = 0, 
            cost: float = 0, note: str = '') -> bool:
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    'SELECT id FROM holdings WHERE code = %s AND status = 1',
                    (code,)
                )
                if cursor.fetchone():
                    return False
                
                now = datetime.now()
                amount = float(shares or 0) * float(cost or 0)
                
                cursor.execute(
                    'INSERT INTO holdings (code, name, shares, cost, amount, profit, profit_pct, note, created_at, updated_at) '
                    'VALUES (%s, %s, %s, %s, %s, 0, 0, %s, %s, %s)',
                    (code, name, shares, cost, amount, note, now, now)
                )
                conn.commit()
                return True
        finally:
            conn.close()
    
    def update(self, code: str, **kwargs) -> bool:
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                fields = []
                params = []
                for k, v in kwargs.items():
                    if v is not None and k in ['name', 'shares', 'cost', 'note', 'nav', 'amount', 'profit', 'profit_pct']:
                        fields.append('%s = %%s' % k)
                        params.append(v)
                
                if not fields:
                    return False
                
                fields.append('updated_at = %s')
                params.append(datetime.now())
                params.append(code)
                
                cursor.execute(
                    'UPDATE holdings SET %s WHERE code = %%s AND status = 1' % ', '.join(fields),
                    tuple(params)
                )
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()
    
    def remove(self, code: str) -> bool:
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    'UPDATE holdings SET status = 0, updated_at = %s WHERE code = %s AND status = 1',
                    (datetime.now(), code)
                )
                conn.commit()
                return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get(self, code: str) -> Optional[Dict]:
        conn = self._get_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    'SELECT * FROM holdings WHERE code = %s AND status = 1',
                    (code,)
                )
                return cursor.fetchone()
        finally:
            conn.close()
