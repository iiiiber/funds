#!/usr/bin/env python3
"""备用市场热点数据源 - 新浪财经行业板块
当 akshare 的东方财富接口不可用时，使用此模块获取板块数据
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import re
import urllib.request
import json
from datetime import datetime
from typing import List, Dict

SINA_HY_URL = "https://vip.stock.finance.sina.com.cn/q/view/newFLJK.php?param=hy&page=1&num=100"


def get_sina_sectors() -> List[Dict]:
    """
    从新浪财经获取行业板块涨跌榜
    返回: [{name, change, rank}, ...]
    """
    try:
        req = urllib.request.Request(SINA_HY_URL, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn/'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            try:
                text = raw.decode('gbk')
            except:
                text = raw.decode('utf-8', errors='ignore')
        
        match = re.search(r'S_Finance_bankuai_hy\s*=\s*(\{.*\})', text, re.DOTALL)
        if not match:
            return []
        
        data = json.loads(match.group(1))
        
        sectors = []
        for key, val in data.items():
            parts = val.split(',')
            if len(parts) >= 5:
                name = parts[1].strip()
                try:
                    change = float(parts[4])
                except:
                    change = 0
                sectors.append({'name': name, 'change': change})
        
        sectors.sort(key=lambda x: x['change'], reverse=True)
        return sectors
    except Exception as e:
        print(f"获取新浪行业板块失败: {e}")
        return []


def get_hot_sectors_fallback() -> List[Dict]:
    """
    获取热点板块（备用数据源）
    取涨幅前5且涨幅>0的板块
    """
    sectors = get_sina_sectors()
    hot = [s for s in sectors if s['change'] > 0][:5]
    return hot


def get_all_sectors_fallback() -> List[Dict]:
    """获取全部板块（备用数据源）"""
    return get_sina_sectors()


if __name__ == '__main__':
    sectors = get_sina_sectors()
    print(f"共获取 {len(sectors)} 个行业板块")
    print("\n涨幅前10:")
    for i, s in enumerate(sectors[:10], 1):
        print(f"  {i}. {s['name']} {s['change']:+.2f}%")
    print("\n跌幅前5:")
    for i, s in enumerate(sectors[-5:], 1):
        print(f"  {i}. {s['name']} {s['change']:+.2f}%")