#!/usr/bin/env python3
"""定时获取基金实际净值（收盘后更新）"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.fund_api import get_realtime_quote, get_historical_nav
from core.holdings import HoldingsManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent.parent / 'data' / 'actual_navs.json'


def get_actual_nav(code: str) -> dict:
    """获取基金的最新实际净值（不是估算净值）"""
    # 从历史净值获取最新的实际单位净值
    hist = get_historical_nav(code, 5)  # 只获取最近5天
    
    if hist:
        latest = hist[-1]  # 最新一条
        return {
            'date': latest['date'],
            'nav': latest['nav'],
            'daily_return': latest.get('daily_return', 0) or 0
        }
    return None


def fetch_all_actual_navs():
    """获取所有持仓基金的最新实际净值"""
    mgr = HoldingsManager()
    holdings = mgr.list()
    
    if not holdings:
        logger.warning("⚠️ 暂无持仓")
        return {}
    
    results = {}
    
    for h in holdings:
        code = h['code']
        logger.info(f"📊 获取 {code} {h['name']} 实际净值...")
        
        actual = get_actual_nav(code)
        if actual:
            logger.info(f"   实际净值: {actual['nav']:.4f} ({actual['date']}) 涨跌: {actual['daily_return']:+.2f}%")
            results[code] = actual
        else:
            # 如果历史净值获取失败，尝试从实时接口获取
            quote = get_realtime_quote(code)
            if quote:
                results[code] = {
                    'date': quote.get('update_time', datetime.now().strftime('%Y-%m-%d')),
                    'nav': quote.get('price', 0),
                    'daily_return': quote.get('change_pct', 0)
                }
                logger.warning(f"   ⚠️ 历史净值获取失败，使用实时数据: {results[code]}")
            else:
                logger.error(f"   ❌ 获取失败")
    
    return results


def save_actual_navs(data: dict, mode: str = 'update'):
    """保存实际净值数据"""
    DATA_FILE.parent.mkdir(exist_ok=True)
    
    if mode == 'update' and DATA_FILE.exists():
        # 增量更新：保留之前的数据，只更新存在的
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        existing.update(data)
        data = existing
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='获取基金实际净值')
    parser.add_argument('--mode', default='update', choices=['update', 'replace'],
                        help='update=增量更新, replace=全量替换')
    args = parser.parse_args()
    
    logger.info("=" * 50)
    logger.info(f"📡 FundQuant 实际净值获取 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    logger.info("=" * 50)
    
    results = fetch_all_actual_navs()
    
    if results:
        save_actual_navs(results, args.mode)
        logger.info(f"\n✅ 数据已保存到 {DATA_FILE}")
    else:
        logger.error("\n❌ 未获取到任何数据")
    
    logger.info("=" * 50)


if __name__ == '__main__':
    main()
