"""Flask Web 应用 - FundQuant 基金量化助手"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 加载.env环境变量
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

from flask import Flask, jsonify, render_template, request
import json
from datetime import datetime
import re

# JSON序列化处理datetime
def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

from core.enhanced_analyzer import generate_comprehensive_analysis
from core.fund_api import get_realtime_quote, get_historical_nav, POPULAR_FUNDS
from core.holdings import HoldingsManager
from core.analysis import analyze_fund, calculate_volatility, calculate_sharpe_ratio
from core.recommender import SmartRecommender, ALL_FUND_POOL, FUND_CATEGORIES, quick_recommend

# AI分析模块
try:
    from core.ai_client import FundAIAnalyzer
    AI_ANALYZER = FundAIAnalyzer()  # 从数据库读取配置
except ImportError:
    AI_ANALYZER = None

app = Flask(__name__, template_folder='templates')
mgr = HoldingsManager()
recommender = SmartRecommender()


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/holdings')
def api_holdings():
    """获取持仓列表"""
    holdings = mgr.list()
    
    result = []
    for h in holdings:
        quote = get_realtime_quote(h['code'])
        # 获取昨日净值和涨跌
        hist = get_historical_nav(h['code'], 5)
        yesterday_nav = None
        yesterday_chg = None
        if hist and len(hist) >= 2:
            yesterday_nav = hist[-2]['nav']
            yesterday_chg = hist[-2]['daily_return']
        if quote:
            cost = h.get('cost', 0)
            profit_pct = ((quote["price"] - float(cost)) / float(cost) * 100) if float(cost) > 0 else 0
            result.append({
                **h,
                'current_nav': quote['price'],
                'change_pct': quote['change_pct'],
                'profit_pct': round(profit_pct, 2),
                'update_time': quote['update_time'],
                'yesterday_nav': yesterday_nav,
                'yesterday_chg': yesterday_chg,
            })
        else:
            result.append({**h, 'error': '获取失败', 'yesterday_nav': yesterday_nav, 'yesterday_chg': yesterday_chg})
    
    return jsonify({'success': True, 'data': result})


@app.route('/api/holdings', methods=['POST'])
def api_add_holding():
    """添加持仓"""
    data = request.json
    code = data.get('code', '').strip()
    name = data.get('name', '')
    
    if not code:
        return jsonify({'success': False, 'error': '请输入基金代码'})
    
    if not name:
        quote = get_realtime_quote(code)
        if quote:
            name = quote['name']
    
    success = mgr.add(
        code=code,
        name=name,
        shares=data.get('shares', 0),
        cost=data.get('cost', 0),
        note=data.get('note', '')
    )
    
    return jsonify({'success': success, 'message': f'已添加 {name}' if success else '该基金已存在'})


@app.route('/api/holdings/<code>', methods=['PUT'])
def api_update_holding(code):
    """更新持仓信息"""
    data = request.json
    update_fields = {}
    if 'shares' in data:
        update_fields['shares'] = float(data['shares'])
    if 'cost' in data:
        update_fields['cost'] = float(data['cost'])
    if 'note' in data:
        update_fields['note'] = data['note']
    if 'name' in data:
        update_fields['name'] = data['name']
    if not update_fields:
        return jsonify({'success': False, 'error': '没有需要更新的字段'})
    success = mgr.update(code, **update_fields)
    if success:
        return jsonify({'success': True, 'message': f'已更新 {code}'})
    else:
        return jsonify({'success': False, 'error': '更新失败'})


@app.route('/api/holdings/<code>', methods=['DELETE'])
def api_delete_holding(code):
    """删除持仓"""
    success = mgr.remove(code)
    return jsonify({'success': success})


@app.route('/api/fund/<code>')
def api_fund_detail(code):
    """获取基金详情"""
    quote = get_realtime_quote(code)
    nav_list = get_historical_nav(code, 90)
    
    return jsonify({
        'success': True,
        'quote': quote,
        'nav_list': nav_list[:30] if nav_list else []
    })


@app.route('/api/analyze/<code>')
def api_analyze(code):
    """增强版AI量化分析 - 整合持仓+市场动态"""
    # 获取持仓信息
    holdings = mgr.list()
    holding_info = None
    for h in holdings:
        if h['code'] == code:
            holding_info = {
                'shares': h.get('shares', 0),
                'cost': h.get('cost', 0),
                'amount': h.get('amount', 0),
                'profit': h.get('profit', 0),
                'profit_pct': h.get('profit_pct', 0),
                'change_pct': h.get('change_pct', 0),
            }
            break
    
    # 调用增强版分析
    result = generate_comprehensive_analysis(code, holding_info)
    
    if result.get('success'):
        return jsonify({'success': True, 'data': result})
    else:
        return jsonify({'success': False, 'error': result.get('error', '分析失败')})

@app.route('/api/recommend')
def api_recommend():
    """智能推荐"""
    rec_type = request.args.get('type', 'momentum')
    category = request.args.get('category', 'all')
    limit = int(request.args.get('limit', 9))
    
    holdings = mgr.list()
    exclude_codes = [h['code'] for h in holdings]
    
    results = quick_recommend(
        recommend_type=rec_type,
        category=category,
        exclude_codes=exclude_codes,
        limit=limit,
        get_nav_func=get_historical_nav
    )
    
    # 补充实时行情
    for r in results:
        quote = get_realtime_quote(r['code'])
        if quote:
            r['current_nav'] = quote.get('price')
            r['change_pct'] = quote.get('change_pct')
            r['update_time'] = quote.get('update_time')
        
        # 获取分类名
        for cat_name, (cat_label, cat_codes) in FUND_CATEGORIES.items():
            if r['code'] in cat_codes:
                r['category'] = cat_label
                break
    
    fund_pool = FUND_CATEGORIES.get(category, FUND_CATEGORIES['all'])[1]
    
    return jsonify({
        'success': True,
        'data': results,
        'recommend_type': rec_type,
        'category': category,
        'total_candidates': len(fund_pool)
    })


@app.route('/api/recommend/similar')
def api_similar():
    """查找相似基金"""
    code = request.args.get('code', '')
    limit = int(request.args.get('limit', 5))
    
    holdings = mgr.list()
    exclude_codes = [h['code'] for h in holdings]
    
    results = recommender.find_similar_funds(
        target_code=code,
        fund_pool=list(ALL_FUND_POOL.keys()),
        fund_names=ALL_FUND_POOL,
        exclude_codes=exclude_codes,
        limit=limit,
        get_nav_func=get_historical_nav
    )
    
    return jsonify({'success': True, 'data': results})


@app.route('/api/recommend/portfolio')
def api_portfolio():
    """组合分析"""
    holdings = mgr.list()
    
    if not holdings:
        return jsonify({
            'success': False,
            'error': '请先添加持仓'
        })
    
    analysis = recommender.get_portfolio_analysis(holdings, get_historical_nav)
    
    # 获取配置建议
    exclude_codes = [h['code'] for h in holdings]
    recommendations = quick_recommend(
        recommend_type='diversify',
        category='all',
        exclude_codes=exclude_codes,
        limit=3,
        get_nav_func=get_historical_nav
    )
    analysis['recommendations'] = recommendations
    
    return jsonify({'success': True, 'data': analysis})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
