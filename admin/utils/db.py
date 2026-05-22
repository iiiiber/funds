"""数据库连接工具"""
import pymysql
from contextlib import contextmanager
from datetime import datetime

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'funds',
    'password': '6NZ7Hp2Z5YWShARJ',
    'database': 'funds',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

@contextmanager
def get_db():
    """获取数据库连接上下文"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def execute_query(sql, params=None, one=False):
    """执行查询"""
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone() if one else cursor.fetchall()

def execute_write(sql, params=None):
    """执行写操作"""
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.lastrowid
