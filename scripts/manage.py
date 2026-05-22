#!/usr/bin/env python3
"""
FundQuant 管理脚本
管理持仓、Web服务、定时任务
"""
import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.holdings import HoldingsManager
from core.fund_api import get_realtime_quote, POPULAR_FUNDS


def cmd_holdings(args):
    """持仓管理命令"""
    mgr = HoldingsManager()
    
    if args.list:
        holdings = mgr.list()
        if not holdings:
            print("📋 暂无持仓\n")
        else:
            print("📋 当前持仓:\n")
            for h in holdings:
                print(f"  {h['code']:8} {h['name']:20} {h.get('cost', 0):.4f}")
        return
    
    if args.add:
        code = args.add[0]
        name = args.add[1] if len(args.add) > 1 else ""
        shares = float(args.add[2]) if len(args.add) > 2 else 0
        cost = float(args.add[3]) if len(args.args) > 3 else 0
        
        # 自动获取基金名称
        if not name:
            quote = get_realtime_quote(code)
            name = quote.get('name', code) if quote else code
        
        if mgr.add(code, name, shares, cost):
            print(f"✅ 已添加: {code} {name}")
        else:
            print(f"⚠️ {code} 已存在")
        return
    
    if args.remove:
        code = args.remove
        if mgr.remove(code):
            print(f"🗑️ 已删除: {code}")
        else:
            print(f"⚠️ 未找到: {code}")
        return
    
    if args.update:
        code = args.update[0]
        kwargs = {}
        for arg in args.update[1:]:
            if '=' in arg:
                k, v = arg.split('=', 1)
                try:
                    kwargs[k] = float(v)
                except:
                    kwargs[k] = v
        if mgr.update(code, **kwargs):
            print(f"✅ 已更新: {code}")
        else:
            print(f"⚠️ 未找到: {code}")
        return
    
    print("用法:")
    print("  holdings --list              # 列出持仓")
    print("  holdings --add CODE [NAME] [SHARES] [COST]  # 添加")
    print("  holdings --remove CODE       # 删除")
    print("  holdings --update CODE KEY=VALUE...  # 更新")


def cmd_status(args):
    """状态命令"""
    mgr = HoldingsManager()
    holdings = mgr.list()
    
    print("=" * 50)
    print("📊 FundQuant 状态")
    print("=" * 50)
    print(f"📈 持仓基金: {len(holdings)} 只")
    print()
    
    if holdings:
        total_cost = 0
        total_value = 0
        
        for h in holdings:
            quote = get_realtime_quote(h['code'])
            if quote:
                nav = quote.get('estimated_nav') or quote.get('price', 0)
                cost = h.get('cost', 0)
                shares = h.get('shares', 0)
                
                value = nav * shares
                cost_total = cost * shares
                
                profit = value - cost_total
                profit_pct = (nav - cost) / cost * 100 if cost > 0 else 0
                
                emoji = "🟢" if profit >= 0 else "🔴"
                sign = "+" if profit >= 0 else ""
                
                print(f"{emoji} {h['name']}")
                print(f"   {h['code']} | 净值 {nav:.4f} | {sign}{profit_pct:.2f}%")
                
                total_cost += cost_total
                total_value += value
        
        if total_cost > 0:
            total_profit = total_value - total_cost
            total_profit_pct = total_profit / total_cost * 100
            sign = "+" if total_profit >= 0 else ""
            
            print()
            print("─" * 30)
            print(f"💎 总市值: ¥{total_value:.2f}")
            print(f"💵 总成本: ¥{total_cost:.2f}")
            print(f"💰 总盈亏: {sign}¥{total_profit:.2f} ({sign}{total_profit_pct:.2f}%)")


def cmd_search(args):
    """搜索基金"""
    query = args.query
    
    print(f"🔍 搜索: {query}\n")
    
    # 搜索热门基金
    for code, name in POPULAR_FUNDS.items():
        if query.lower() in name.lower() or query.lower() in code.lower():
            quote = get_realtime_quote(code)
            if quote:
                print(f"  📈 {code} {name}")
                print(f"     净值: {quote['price']:.4f} ({quote['change_pct']:+.2f}%)")
                print()


def cmd_server(args):
    """启动服务器"""
    from app.main import run
    port = args.port or 8080
    print(f"🚀 启动服务器: http://localhost:{port}")
    run(port)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='FundQuant 管理工具')
    subparsers = parser.add_subparsers(dest='cmd', help='子命令')
    
    # holdings 子命令
    p_holdings = subparsers.add_parser('holdings', help='持仓管理')
    p_holdings.add_argument('--list', action='store_true', help='列出持仓')
    p_holdings.add_argument('--add', nargs='+', help='添加基金: CODE [NAME] [SHARES] [COST]')
    p_holdings.add_argument('--remove', help='删除基金')
    p_holdings.add_argument('--update', nargs='+', help='更新基金')
    p_holdings.set_defaults(func=cmd_holdings)
    
    # status 子命令
    p_status = subparsers.add_parser('status', help='查看状态')
    p_status.set_defaults(func=cmd_status)
    
    # search 子命令
    p_search = subparsers.add_parser('search', help='搜索基金')
    p_search.add_argument('query', help='搜索关键词')
    p_search.set_defaults(func=cmd_search)
    
    # server 子命令
    p_server = subparsers.add_parser('server', help='启动Web服务')
    p_server.add_argument('-p', '--port', type=int, help='端口号')
    p_server.set_defaults(func=cmd_server)
    
    args = parser.parse_args()
    
    if args.cmd and hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
