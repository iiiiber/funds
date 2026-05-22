"""动态基金池获取模块 - 从东方财富API获取热门ETF"""
import json
import logging
import time
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# 缓存
_fund_pool_cache = {
    'data': {},
    'timestamp': 0,
    'ttl': 3600  # 缓存1小时
}

def get_hot_etf_list(sort: str = 'f6', limit: int = 200) -> List[Dict]:
    """
    从东方财富获取热门ETF基金列表
    
    Args:
        sort: 排序字段
            f3  = 涨跌幅
            f6  = 成交额（默认）
            f104 = 规模
        limit: 返回数量
    
    Returns:
        [{code, name, change_pct, volume, scale}, ...]
    """
    import urllib.request
    
    # 按成交额排序的ETF
    url = (f"https://push2.eastmoney.com/api/qt/clist/get?"
           f"pn=1&pz={limit}&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
           f"&fltt=2&invt=2&fid={sort}&order=desc"
           f"&fs=b:MK0021&fields=f12,f14,f3,f6,f104")
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode('utf-8')
        
        data = json.loads(text)
        funds = data.get('data', {}).get('diff', [])
        
        result = []
        for f in funds:
            code = f.get('f12', '')
            name = f.get('f14', '')
            if code and name:
                result.append({
                    'code': code,
                    'name': name,
                    'change_pct': f.get('f3', 0),
                    'volume': f.get('f6', 0),
                    'scale': f.get('f104', '-'),
                })
        return result
    except Exception as e:
        logger.error(f"获取东方财富ETF失败: {e}")
        return []


def get_qdii_etf_list(limit: int = 50) -> List[Dict]:
    """获取QDII海外ETF"""
    import urllib.request
    
    url = (f"https://push2.eastmoney.com/api/qt/clist/get?"
           f"pn=1&pz={limit}&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
           f"&fltt=2&invt=2&fid=f6&order=desc"
           f"&fs=b:MK0405&fields=f12,f14,f3,f6,f104")  # b:MK0405 = QDII
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode('utf-8')
        
        data = json.loads(text)
        funds = data.get('data', {}).get('diff', [])
        
        result = []
        for f in funds:
            code = f.get('f12', '')
            name = f.get('f14', '')
            if code and name:
                result.append({
                    'code': code,
                    'name': name,
                    'change_pct': f.get('f3', 0),
                    'volume': f.get('f6', 0),
                })
        return result
    except Exception as e:
        logger.error(f"获取QDII ETF失败: {e}")
        return []


def classify_etf(funds: List[Dict]) -> Dict[str, List[Dict]]:
    """将ETF按类型分类"""
    categories = {
        'broad_index': {
            'name': '宽基指数',
            'keywords': ['沪深300', '中证500', '创业板', '科创50', '科创板', '上证50', '中证100', 
                        '中证A50', '中证A500', 'A500', 'MSCI', '富时', '道琼斯'],
        },
        'industry': {
            'name': '行业主题',
            'keywords': ['芯片', '半导体', '新能源', '光伏', '医疗', '医药', '消费', '白酒', 
                        '军工', '证券', '银行', '房地产', '钢铁', '煤炭', '有色', '化工',
                        '5G', '通信', '人工智能', 'AI', '计算机', '软件', '互联网', '游戏',
                        '传媒', '教育', '农业', '养殖', '食品', '家电', '汽车', '电力'],
        },
        'qdii': {
            'name': '海外QDII',
            'keywords': ['纳斯达克', '日经', '恒生', '越南', '标普', '德国', '法国', '英国',
                        '美国', '港股', '亚太', '欧洲', '全球', '海外', '印度', '东南亚'],
        },
        'commodity': {
            'name': '商品贵金属',
            'keywords': ['黄金', '白银', '原油', '石油', '大宗商品', '商品', '豆粕', '玉米'],
        },
    }
    
    result = {k: [] for k in categories}
    result['other'] = []
    
    for f in funds:
        name = f['name']
        classified = False
        for cat_id, cat_info in categories.items():
            for kw in cat_info['keywords']:
                if kw in name:
                    result[cat_id].append(f)
                    classified = True
                    break
            if classified:
                break
        if not classified:
            result['other'].append(f)
    
    return result


def get_dynamic_fund_pool(max_per_category: int = 30, force_refresh: bool = False) -> Dict[str, Dict[str, str]]:
    """
    获取动态基金池（按类别分组）
    
    Args:
        max_per_category: 每个类别最多保留数量
        force_refresh: 强制刷新缓存
    
    Returns:
        {
            'broad_index': {'code': 'name', ...},
            'industry': {'code': 'name', ...},
            'qdii': {'code': 'name', ...},
            'commodity': {'code': 'name', ...},
            'all': {'code': 'name', ...},
        }
    """
    global _fund_pool_cache
    
    current_time = time.time()
    
    # 检查缓存
    if (not force_refresh and 
        _fund_pool_cache['data'] and 
        current_time - _fund_pool_cache['timestamp'] < _fund_pool_cache['ttl']):
        return _fund_pool_cache['data']
    
    # 获取数据
    etf_list = get_hot_etf_list('f6', 300)
    qdii_list = get_qdii_etf_list(100)
    
    # 合并
    all_funds = etf_list + qdii_list
    classified = classify_etf(all_funds)
    
    # 转换为 code->name 格式
    result = {}
    for cat, funds in classified.items():
        result[cat] = {f['code']: f['name'] for f in funds[:max_per_category]}
    
    # 全部
    result['all'] = {}
    for cat, funds_dict in result.items():
        if cat != 'all':
            result['all'].update(funds_dict)
    
    # 更新缓存
    _fund_pool_cache['data'] = result
    _fund_pool_cache['timestamp'] = current_time
    
    logger.info(f"动态基金池已更新: 宽基{len(result.get('broad_index', {}))}只, "
                 f"行业{len(result.get('industry', {}))}只, "
                 f"QDII{len(result.get('qdii', {}))}只, "
                 f"商品{len(result.get('commodity', {}))}只, "
                 f"总计{len(result.get('all', {}))}只")
    
    return result


def get_pool_stats() -> Dict:
    """获取基金池统计信息"""
    pool = get_dynamic_fund_pool()
    return {
        'broad_index': len(pool.get('broad_index', {})),
        'industry': len(pool.get('industry', {})),
        'qdii': len(pool.get('qdii', {})),
        'commodity': len(pool.get('commodity', {})),
        'all': len(pool.get('all', {})),
        'cached': _fund_pool_cache['timestamp'] > 0,
        'last_update': time.strftime('%Y-%m-%d %H:%M:%S', 
                                     time.localtime(_fund_pool_cache['timestamp'])) 
                        if _fund_pool_cache['timestamp'] else '从未更新',
    }


if __name__ == '__main__':
    # 测试
    print("=" * 60)
    print("动态基金池获取测试")
    print("=" * 60)
    
    pool = get_dynamic_fund_pool(force_refresh=True)
    stats = get_pool_stats()
    
    print(f"\n📊 基金池统计:")
    for k, v in stats.items():
        print(f"   {k}: {v}")
    
    print(f"\n📈 宽基指数 (前10):")
    for code, name in list(pool['broad_index'].items())[:10]:
        print(f"   {code} {name}")
    
    print(f"\n📈 行业主题 (前10):")
    for code, name in list(pool['industry'].items())[:10]:
        print(f"   {code} {name}")
