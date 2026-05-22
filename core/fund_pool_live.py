#!/usr/bin/env python3
"""动态基金池 - 从东方财富实时抓取热门ETF（自动更新版）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import json
from datetime import datetime

# 缓存时间（秒）：5分钟内不重复请求
CACHE_TTL = 300

# 全局缓存
_cache = {
    'pool_by_category': None,
    'all_pool': None,
    'timestamp': 0,
}

# 分类关键词
CATEGORY_KEYWORDS = {
    '宽基指数': [
        '沪深300', '中证500', '中证1000', '中证A50', 'A500', '创业板50', '创业板',
        '科创50', '科创100', '上证50', '上证指数', '深证100', '红利', '低波',
        'MSCI', '纳指', '标普', '道琼斯', '恒生', '港股', '日经', '越南',
        '中证2000', '中证800', '中证A100', '中证红利'
    ],
    '行业': [
        '芯片', '半导体', '人工智能', 'AI', '通信', '5G', '计算机', '软件', '电子',
        '新能源', '光伏', '储能', '电池', '汽车', '智能驾驶', '军工', '航天', '航空',
        '医疗', '医药', '生物', '创新药', '中药', '医疗器械', '券商', '银行', '保险',
        '食品', '白酒', '消费', '家电', '旅游', '零售', '农业', '养殖', '畜牧',
        '稀土', '稀有金属', '有色', '煤炭', '钢铁', '化工', '石油', '天然气',
        '影视', '游戏', '传媒', '教育', '房地产', '建材', '建筑', '工程机械',
        '卫星', '海工', '机械设备', '机器人'
    ],
    '商品': [
        '黄金', '白银', '原油', '大宗商品', '商品', '油气', '能源', '铜', '铝'
    ]
}


def _classify_name(name: str) -> str:
    """根据基金名称分类"""
    name_upper = name.upper()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.upper() in name_upper:
                return cat
    return '其他'


def get_etf_pool(force_refresh: bool = False) -> dict:
    """
    获取动态ETF基金池（自动从东方财富抓取）
    """
    global _cache
    
    now = time.time()
    
    # 检查缓存
    if not force_refresh and _cache['pool_by_category'] and (now - _cache['timestamp']) < CACHE_TTL:
        return _cache['pool_by_category']
    
    try:
        import akshare as ak
        import pandas as pd
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 从东方财富抓取ETF数据...")
        df = ak.fund_etf_spot_em()
        print(f"  获取到 {len(df)} 只ETF")
        
        # 过滤：成交额>5000万
        df = df.copy()
        df['_成交额'] = pd.to_numeric(df['成交额'], errors='coerce').fillna(0)
        hot = df[df['_成交额'] > 50_000_000].sort_values('_成交额', ascending=False)
        print(f"  过滤后（成交额>5000万）: {len(hot)} 只")
        
        # 分类
        pools = {'宽基指数': {}, '行业': {}, '商品': {}, '其他': {}}
        
        for _, row in hot.iterrows():
            code = str(row['代码']).strip()
            name = str(row['名称']).strip()
            if len(code) != 6 or not code.isdigit():
                continue
            
            cat = _classify_name(name)
            if len(pools[cat]) < 50:
                pools[cat][code] = name
        
        # 合并ALL
        all_pool = {}
        for cat in ['宽基指数', '行业', '商品', '其他']:
            all_pool.update(pools.get(cat, {}))
        
        total = len(all_pool)
        print(f"  分类完成，总计: {total} 只")
        
        result = {
            **pools,
            '_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            '_total': total,
            '_source': 'eastmoney',
        }
        
        _cache['pool_by_category'] = result
        _cache['all_pool'] = all_pool
        _cache['timestamp'] = now
        
        return result
        
    except Exception as e:
        print(f"  抓取失败: {e}")
        if _cache['pool_by_category']:
            print("  使用过期缓存")
            return _cache['pool_by_category']
        return {
            '宽基指数': {}, '行业': {}, '商品': {}, '其他': {},
            '_updated': '获取失败', '_total': 0, '_error': str(e)
        }


def get_live_fund_pool() -> dict:
    """获取分类基金池"""
    return get_etf_pool()


def get_all_live_pool() -> dict:
    """获取全部基金（合并）"""
    global _cache
    if _cache['all_pool'] is None:
        get_etf_pool()
    return _cache['all_pool'] or {}


# 兼容旧接口 - 首次导入时预加载
print("首次加载ETF基金池（东方财富实时数据）...")
_default_pool = get_etf_pool()
LIVE_FUND_POOL = {
    '宽基指数': _default_pool.get('宽基指数', {}),
    '行业': _default_pool.get('行业', {}),
    '商品': _default_pool.get('商品', {}),
    '其他': _default_pool.get('其他', {}),
}
ALL_LIVE_POOL = {}
for cat in ['宽基指数', '行业', '商品', '其他']:
    ALL_LIVE_POOL.update(LIVE_FUND_POOL.get(cat, {}))


# 每隔300秒自动更新缓存（在下次访问时生效）
def refresh_pool():
    """手动刷新基金池"""
    global LIVE_FUND_POOL, ALL_LIVE_POOL
    pool = get_etf_pool(force_refresh=True)
    LIVE_FUND_POOL = {
        '宽基指数': pool.get('宽基指数', {}),
        '行业': pool.get('行业', {}),
        '商品': pool.get('商品', {}),
        '其他': pool.get('其他', {}),
    }
    ALL_LIVE_POOL = {}
    for cat in ['宽基指数', '行业', '商品', '其他']:
        ALL_LIVE_POOL.update(LIVE_FUND_POOL.get(cat, {}))
    return pool


if __name__ == '__main__':
    pool = get_etf_pool()
    print("\n=== 基金池统计 ===")
    for cat in ['宽基指数', '行业', '商品', '其他']:
        count = len(pool.get(cat, {}))
        print(f"  {cat}: {count} 只")
    print(f"\n更新时间: {pool.get('_updated')}")
    print(f"总计: {pool.get('_total')} 只")