#!/usr/bin/env python3
"""
FundQuant 定时任务脚本
- 获取基金行情
- 生成日报
- 发送飞书通知

用法:
    python3 scripts/daily_report.py          # 手动运行
    python3 scripts/daily_report.py --cron   # 定时模式(静默)
"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.fund_api import get_realtime_quote
from core.holdings import HoldingsManager
from core.notify import FeishuNotifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def get_quotes_for_holdings():
    """获取所有持仓基金的行情"""
    mgr = HoldingsManager()
    holdings = mgr.list()
    
    if not holdings:
        logger.warning("没有持仓数据")
        return [], []
    
    results = []
    for h in holdings:
        quote = get_realtime_quote(h['code'])
        if quote:
            cost = h.get('cost', 0)
            shares = h.get('shares', 0)
            
            # 计算盈亏
            current_nav = quote.get('estimated_nav') or quote.get('price', 0)
            if cost > 0 and shares > 0:
                profit = (current_nav - cost) * shares
                profit_pct = (current_nav - cost) / cost * 100
            else:
                profit = 0
                profit_pct = 0
            
            results.append({
                'code': h['code'],
                'name': h.get('name', quote.get('name', h['code'])),
                'shares': shares,
                'cost': cost,
                'current_nav': current_nav,
                'change_pct': quote.get('change_pct', 0),
                'profit': round(profit, 2),
                'profit_pct': round(profit_pct, 2),
                'update_time': quote.get('update_time', ''),
            })
            logger.info(f"✅ {h['code']}: {quote.get('price', 'N/A')} ({quote.get('change_pct', 0):+.2f}%)")
        else:
            logger.error(f"❌ 获取 {h['code']} 行情失败")
    
    return holdings, results


def generate_report(holdings: list, quotes: list) -> str:
    """生成日报文本"""
    if not quotes:
        return "📊 暂无基金数据"
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    lines = [f"📊 **FundQuant 基金日报**\n📅 {now}\n\n"]
    
    # 统计
    total_cost = 0
    total_value = 0
    green_count = 0
    red_count = 0
    
    for q in quotes:
        cost = q['cost']
        shares = q['shares']
        
        if cost > 0 and shares > 0:
            cost_total = cost * shares
            value_total = q['current_nav'] * shares
            profit = value_total - cost_total
            profit_pct = q['profit_pct']
        else:
            cost_total = 0
            value_total = 0
            profit = q['profit']
            profit_pct = q['profit_pct']
        
        total_cost += cost_total
        total_value += value_total
        
        if profit >= 0:
            green_count += 1
            emoji = "🟢"
            sign = "+"
        else:
            red_count += 1
            emoji = "🔴"
            sign = ""
        
        # 基金名称
        name = q['name'][:12]
        if len(q['name']) > 12:
            name += '…'
        
        lines.append(f"{emoji} **{name}**\n")
        lines.append(f"   📈 净值: `{q['current_nav']:.4f}` ({q['change_pct']:+.2f}%)\n")
        
        if cost > 0:
            lines.append(f"   💵 成本: `{cost:.4f}` → `{q['current_nav']:.4f}`\n")
            lines.append(f"   💰 盈亏: `{sign}{profit:.2f}`元 (`{sign}{profit_pct:.2f}%`)\n")
        
        lines.append("\n")
    
    # 汇总
    lines.append("─" * 20 + "\n")
    
    total_profit = total_value - total_cost
    if total_cost > 0:
        total_profit_pct = total_profit / total_cost * 100
        sign = "+" if total_profit >= 0 else ""
        
        lines.append(f"📈 持仓总数: **{len(quotes)}** 只\n")
        lines.append(f"🟢 盈利: **{green_count}** 只\n")
        lines.append(f"🔴 亏损: **{red_count}** 只\n")
        lines.append(f"\n💎 总市值: `¥{total_value:.2f}`\n")
        lines.append(f"💵 总成本: `¥{total_cost:.2f}`\n")
        lines.append(f"💰 总盈亏: `{sign}{total_profit:.2f}`元 (`{sign}{total_profit_pct:.2f}%`)\n")
    
    lines.append(f"\n🤖 via FundQuant")
    
    return ''.join(lines)


def main():
    """主函数"""
    is_cron = '--cron' in sys.argv
    
    if not is_cron:
        print("=" * 50)
        print("📊 FundQuant 基金日报生成器")
        print("=" * 50)
        print()
    
    # 获取行情
    holdings, quotes = get_quotes_for_holdings()
    
    if not quotes:
        logger.error("没有获取到任何行情数据")
        sys.exit(1)
    
    # 生成报告
    report = generate_report(holdings, quotes)
    
    if not is_cron:
        print("\n" + report)
    
    # 保存报告
    report_file = Path(__file__).parent.parent / 'data' / 'daily_report.md'
    report_file.parent.mkdir(exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    logger.info(f"报告已保存: {report_file}")
    
    # 发送通知
    notifier = FeishuNotifier()
    if notifier.webhook_url:
        if not is_cron:
            print("\n⚠️ 飞书 webhook 未配置，跳过通知")
            print("   请在 config.yaml 中设置 notification.feishu.webhook_url")
    else:
        if notifier.send(report, msg_type="markdown"):
            logger.info("✅ 飞书通知已发送")
        else:
            logger.error("❌ 飞书通知发送失败")
    
    if not is_cron:
        print("\n" + "=" * 50)
        print("✅ 完成!")
        print("=" * 50)


if __name__ == '__main__':
    main()
