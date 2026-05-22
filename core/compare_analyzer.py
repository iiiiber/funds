#!/usr/bin/env python3
"""持仓对比分析模块 - 方案B新增
对比多只基金的收益/风险/技术面，给出横向评估结论
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from core.fund_analyzer import FundAnalyzer
from core.analysis import calculate_volatility, calculate_sharpe_ratio, calculate_max_drawdown
from core.fund_api import get_historical_nav
from core.enhanced_analyzer import calculate_technical_indicators


def analyze_single_fund(code: str) -> dict:
    """对单只基金做完整指标计算"""
    data = {
        'code': code,
        'name': '',
        'current_nav': 0,
        'change_pct': 0,
        'metrics': {},
        'technical': {},
        'score': 50,
        'factors': [],
    }

    try:
        from core.fund_api import get_realtime_quote
        quote = get_realtime_quote(code)
        if quote:
            data['name'] = quote.get('name', code)
            data['current_nav'] = quote.get('price', 0)
            data['change_pct'] = quote.get('change_pct', 0)

        nav_list = get_historical_nav(code, 250)
        if not nav_list or len(nav_list) < 5:
            return data

        prices = [h['nav'] for h in nav_list]

        data['metrics'] = {
            'return_1m': round((prices[-1] - prices[-22]) / prices[-22] * 100, 2) if len(prices) >= 22 else 0,
            'return_3m': round((prices[-1] - prices[-65]) / prices[-65] * 100, 2) if len(prices) >= 65 else 0,
            'return_6m': round((prices[-1] - prices[-130]) / prices[-130] * 100, 2) if len(prices) >= 130 else 0,
            'return_1y': round((prices[-1] - prices[-250]) / prices[-250] * 100, 2) if len(prices) >= 250 else 0,
            'volatility': round(calculate_volatility(nav_list) * 100, 2),
            'sharpe': round(calculate_sharpe_ratio(nav_list), 2),
            'max_drawdown': round(calculate_max_drawdown(nav_list) * 100, 2),
        }

        data['technical'] = calculate_technical_indicators(nav_list)

        # 简单评分
        s = 50
        m = data['metrics']
        t = data['technical']

        if 5 < m['return_1m'] < 15: s += 8
        elif m['return_1m'] > 15: s += 3
        elif m['return_1m'] < -10: s -= 8

        if m['return_3m'] > 15: s += 8
        elif m['return_3m'] < -15: s -= 8

        if m['sharpe'] > 2: s += 12
        elif m['sharpe'] > 1.5: s += 8
        elif m['sharpe'] > 1: s += 4

        if m['max_drawdown'] < 10: s += 8
        elif m['max_drawdown'] > 25: s -= 10

        if '强势' in t.get('trend', '') or '偏强' in t.get('trend', ''): s += 8
        elif '弱势' in t.get('trend', '') or '偏弱' in t.get('trend', ''): s -= 8

        data['score'] = max(0, min(100, s))

        # 评分因素
        if m['return_1m'] > 0:
            data['factors'].append(f"近1月{m['return_1m']:+.1f}%")
        if m['sharpe'] > 1.5:
            data['factors'].append(f"夏普{m['sharpe']:.2f}优秀")
        if m['max_drawdown'] < 15:
            data['factors'].append(f"回撤{m['max_drawdown']:.1f}%可控")
        if '强势' in t.get('trend', ''):
            data['factors'].append(t.get('trend'))

    except Exception as e:
        data['error'] = str(e)

    return data


def compare_funds(codes: list) -> dict:
    """
    对比多只基金（最多5只）
    返回横向对比结果和综合建议
    """
    result = {
        'success': False,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'funds': [],
        'comparison': {},
        'winner': None,
        'analysis': '',
    }

    if not codes or len(codes) < 2:
        result['error'] = '至少需要2只基金'
        return result

    codes = codes[:5]  # 最多5只

    # 分析每只基金
    for code in codes:
        fund_data = analyze_single_fund(code)
        result['funds'].append(fund_data)

    if len(result['funds']) < 2:
        result['error'] = '有效基金数据不足'
        return result

    # 构建对比表
    comparison = {
        'metrics': ['return_1m', 'return_3m', 'return_6m', 'return_1y', 'volatility', 'sharpe', 'max_drawdown'],
        'scores': {},
    }

    metrics_labels = {
        'return_1m': '近1月收益',
        'return_3m': '近3月收益',
        'return_6m': '近6月收益',
        'return_1y': '近1年收益',
        'volatility': '波动率',
        'sharpe': '夏普比率',
        'max_drawdown': '最大回撤',
    }

    # 各指标最优
    best = {}
    for metric in comparison['metrics']:
        if metric in ['volatility', 'max_drawdown']:
            # 这两个越低越好
            values = [(f['code'], f['metrics'].get(metric, 999) or 999) for f in result['funds']]
        else:
            # 其他越高越好
            values = [(f['code'], f['metrics'].get(metric, -999) or -999) for f in result['funds']]
        if values:
            values.sort(key=lambda x: x[1], reverse=metric not in ['volatility', 'max_drawdown'])
            best[metric] = values[0][0]

    comparison['best'] = best
    comparison['labels'] = metrics_labels
    result['comparison'] = comparison

    # 综合评分最高
    winner_code = max(result['funds'], key=lambda f: f['score'])['code']
    result['winner'] = winner_code

    # 生成分析文字
    winner_fund = next((f for f in result['funds'] if f['code'] == winner_code), None)

    analysis_parts = []
    analysis_parts.append(f"对比了 {len(result['funds'])} 只基金：")
    for f in result['funds']:
        mark = '🏆' if f['code'] == winner_code else '  '
        analysis_parts.append(f"{mark} {f['name'] or f['code']} 综合评分{f['score']}分")

    analysis_parts.append(f"\n综合推荐：{winner_fund['name'] or winner_code}（评分最高）")

    # 分项最优
    best_details = []
    for metric, label in metrics_labels.items():
        best_code = best.get(metric)
        if best_code:
            bf = next((f for f in result['funds'] if f['code'] == best_code), None)
            if bf:
                val = bf['metrics'].get(metric)
                if val is not None:
                    if metric in ['volatility', 'max_drawdown']:
                        best_details.append(f"{label}最优: {bf['name'][:6]}{val:.1f}%")
                    else:
                        best_details.append(f"{label}最优: {bf['name'][:6]}{val:+.1f}%")

    if best_details:
        analysis_parts.append(f"\n各维度最优：" + " | ".join(best_details[:4]))

    # 风险提示
    high_vol = [f for f in result['funds'] if f['metrics'].get('volatility', 0) > 30]
    if high_vol:
        analysis_parts.append(f"\n⚠️ 高波动基金: {', '.join([f['name'][:6] for f in high_vol[:2]])}波动率偏高，注意风险")

    result['analysis'] = '\n'.join(analysis_parts)
    result['success'] = True

    return result


if __name__ == '__main__':
    import json
    r = compare_funds(['018957', '014855', '011452'])
    print(json.dumps(r, indent=2, ensure_ascii=False))
