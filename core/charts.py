"""FundQuant 图表模块"""
import json
import re
from pathlib import Path
from typing import List, Dict
from datetime import datetime


def generate_nav_chart_data(code: str, nav_history: List[Dict]) -> dict:
    """生成净值走势图数据"""
    if not nav_history:
        return {}
    
    dates = [r['date'] for r in nav_history]
    navs = [float(r['nav'] or 0) for r in nav_history]
    
    if navs:
        base = navs[0]
        norm_navs = [n / base * 100 for n in navs]
    else:
        norm_navs = []
    
    return {'code': code, 'dates': dates, 'navs': navs, 'norm_navs': norm_navs}


def generate_portfolio_chart(holdings: List[Dict], quotes: List[Dict]) -> dict:
    """生成持仓饼图数据"""
    if not holdings:
        return {}
    
    quote_map = {q['code']: q for q in quotes}
    items = []
    total_value = 0
    
    for h in holdings:
        q = quote_map.get(h['code'], {})
        nav = q.get('nav', 0) or q.get('current_nav', 0)
        shares = h.get('shares', 0)
        value = nav * shares
        
        if value > 0:
            total_value += value
            items.append({'code': h['code'], 'name': h.get('name', h['code']), 'value': value})
    
    for item in items:
        item['pct'] = round(item['value'] / total_value * 100, 1) if total_value > 0 else 0
    
    return {'items': items, 'total_value': total_value}


def generate_profit_chart(holdings: List[Dict], quotes: List[Dict]) -> dict:
    """生成盈亏柱状图数据"""
    quote_map = {q['code']: q for q in quotes}
    items = []
    
    for h in holdings:
        q = quote_map.get(h['code'], {})
        cost = h.get('cost', 0)
        shares = h.get('shares', 0)
        nav = q.get('nav', 0) or q.get('current_nav', 0)
        
        if cost > 0 and shares > 0:
            profit = (nav - cost) * shares
            profit_pct = (nav - cost) / cost * 100
            items.append({
                'code': h['code'],
                'name': h.get('name', h['code'])[:10],
                'profit': round(profit, 2),
                'profit_pct': round(profit_pct, 2),
                'color': '#e74c3c' if profit >= 0 else '#27ae60',
            })
    
    return {'items': items}


def generate_html_report(holdings: List[Dict], quotes: List[Dict], 
                        nav_history: Dict[str, List[Dict]]) -> str:
    """生成完整的 HTML 报告（带图表）"""
    portfolio = generate_portfolio_chart(holdings, quotes)
    profit = generate_profit_chart(holdings, quotes)
    
    # 净值图表数据
    nav_chart_data = {}
    for code, history in nav_history.items():
        nav_chart_data[code] = generate_nav_chart_data(code, history)
    
    # 计算汇总
    total_value = portfolio.get('total_value', 0)
    total_profit = sum(i['profit'] for i in profit.get('items', []))
    total_cost = total_value - total_profit
    
    # 生成表格行
    table_rows = ""
    for h, q in zip(holdings, quotes):
        cost = h.get('cost', 0)
        shares = h.get('shares', 0)
        nav = q.get('nav', 0)
        
        p_item = next((p for p in profit.get('items', []) if p['code'] == h['code']), {})
        profit_val = p_item.get('profit', 0)
        profit_pct = p_item.get('profit_pct', 0)
        
        emoji = "🟢" if profit_val >= 0 else "🔴"
        sign = "+" if profit_val >= 0 else ""
        cls = "up" if profit_val >= 0 else "down"
        
        cost_total = cost * shares
        value_total = nav * shares
        
        table_rows += f"""
                <tr>
                    <td>{h.get('name', h['code'])}</td>
                    <td>{h['code']}</td>
                    <td>¥{cost_total:.2f}</td>
                    <td>¥{value_total:.2f}</td>
                    <td class="{cls}">{emoji} {sign}¥{profit_val:.2f} ({sign}{profit_pct:.2f}%)</td>
                </tr>"""
    
    # 替换值
    replacements = {
        '{{TIMESTAMP}}': datetime.now().strftime('%Y-%m-%d %H:%M'),
        '{{TOTAL_VALUE}}': f'¥{total_value:.2f}',
        '{{TOTAL_COST}}': f'¥{total_cost:.2f}',
        '{{TOTAL_PROFIT}}': f'{total_profit:.2f}',
        '{{PROFIT_COLOR}}': '#e74c3c' if total_profit >= 0 else '#27ae60',
        '{{PROFIT_SIGN}}': "+" if total_profit >= 0 else "",
        '{{HOLDINGS_COUNT}}': str(len(holdings)),
        '{{TABLE_ROWS}}': table_rows,
        '{{PORTFOLIO_JSON}}': json.dumps(portfolio, ensure_ascii=False),
        '{{PROFIT_JSON}}': json.dumps(profit, ensure_ascii=False),
        '{{NAV_CHART_JSON}}': json.dumps(nav_chart_data, ensure_ascii=False),
    }
    
    # 读取模板
    template_path = Path(__file__).parent / 'report_template.html'
    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 替换占位符
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)
    
    return html


if __name__ == '__main__':
    print("📊 图表模块已就绪")
