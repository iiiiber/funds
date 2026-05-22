#!/usr/bin/env python3
"""
FundQuant 报告生成器
生成带图表的 HTML 分析报告
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import FundDB
from core.fund_api import get_realtime_quote, get_historical_nav
from core.charts import generate_html_report


def fetch_all_data():
    """获取所有数据"""
    db = FundDB()
    holdings = db.get_holdings()
    
    quotes = []
    nav_history = {}
    
    for h in holdings:
        code = h['code']
        
        # 获取实时行情
        quote = get_realtime_quote(code)
        if quote:
            db.save_quote(
                code, 
                quote.get('name', h.get('name', code)),
                quote.get('estimated_nav') or quote.get('price', 0),
                quote.get('change_pct', 0),
                quote.get('update_time', '')
            )
            
            quotes.append({
                'code': code,
                'name': quote.get('name', h.get('name', code)),
                'nav': quote.get('estimated_nav') or quote.get('price', 0),
                'change_pct': quote.get('change_pct', 0),
            })
        
        # 获取历史净值
        history = get_historical_nav(code, 90)
        if history:
            db.save_nav_history(code, history)
            nav_history[code] = history
    
    return holdings, quotes, nav_history


def main():
    print("=" * 50)
    print("📊 FundQuant 分析报告生成器")
    print("=" * 50)
    
    # 获取数据
    holdings, quotes, nav_history = fetch_all_data()
    
    if not holdings:
        print("\n⚠️ 暂无持仓数据")
        return
    
    print(f"\n📈 获取到 {len(holdings)} 只基金数据")
    
    # 生成报告
    html = generate_html_report(holdings, quotes, nav_history)
    
    # 保存
    output_path = Path(__file__).parent.parent / 'data' / 'report.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ 报告已生成: {output_path}")
    print("   用浏览器打开查看图表")
    
    # 同时打印摘要
    print("\n" + "=" * 50)
    print("📋 持仓摘要")
    print("=" * 50)
    
    total_cost = 0
    total_value = 0
    
    for h, q in zip(holdings, quotes):
        cost = h.get('cost', 0) * h.get('shares', 0)
        value = q.get('nav', 0) * h.get('shares', 0)
        profit = value - cost
        profit_pct = profit / cost * 100 if cost > 0 else 0
        
        total_cost += cost
        total_value += value
        
        emoji = "🟢" if profit >= 0 else "🔴"
        sign = "+" if profit >= 0 else ""
        
        print(f"{emoji} {h.get('name', h['code'])}")
        print(f"   {h['code']} | 净值 {q.get('nav', 0):.4f} | {sign}{profit_pct:.2f}%")
    
    total_profit = total_value - total_cost
    total_profit_pct = total_profit / total_cost * 100 if total_cost > 0 else 0
    sign = "+" if total_profit >= 0 else ""
    
    print()
    print(f"💎 总市值: ¥{total_value:.2f}")
    print(f"💵 总成本: ¥{total_cost:.2f}")
    print(f"💰 总盈亏: {sign}¥{total_profit:.2f} ({sign}{total_profit_pct:.2f}%)")
    print("=" * 50)


if __name__ == '__main__':
    main()
