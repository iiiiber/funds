#!/usr/bin/env python3
"""定时获取基金行情脚本"""
import sys
import json
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.fund_api import get_realtime_quote, get_historical_nav
from core.holdings import HoldingsManager
from core.analysis import analyze_fund

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    print("=" * 50)
    print("📡 FundQuant 基金行情获取")
    print("=" * 50)
    
    # 加载持仓
    mgr = HoldingsManager()
    holdings = mgr.list()
    
    if not holdings:
        print("⚠️ 暂无持仓，请先添加基金")
        return
    
    results = []
    
    for h in holdings:
        code = h['code']
        print(f"\n📊 获取 {code} {h['name']} 行情...")
        
        # 获取实时行情
        quote = get_realtime_quote(code)
        if quote:
            # 计算盈亏
            current_price = quote['price']
            cost = h.get('cost', 0)
            profit_pct = ((current_price - cost) / cost * 100) if cost > 0 else 0
            
            print(f"   最新净值: {current_price:.4f}")
            print(f"   估算涨跌: {quote['change_pct']:+.2f}%")
            print(f"   持仓盈亏: {profit_pct:+.2f}%")
            
            results.append({
                **h,
                'current_nav': current_price,
                'change_pct': quote['change_pct'],
                'profit_pct': round(profit_pct, 2),
                'update_time': quote['update_time'],
            })
        else:
            print(f"   ❌ 获取失败")
            results.append({**h, 'error': '获取失败'})
    
    # 保存结果
    output_file = Path(__file__).parent.parent / 'data' / 'quotes.json'
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据已保存到 {output_file}")
    print("=" * 50)


if __name__ == '__main__':
    main()
