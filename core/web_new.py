"""Flask Web 应用 - 基金量化助手"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, jsonify, render_template, request
import json

from core.fund_api import get_realtime_quote, get_historical_nav, POPULAR_FUNDS
from core.holdings import HoldingsManager
from core.recommender import SmartRecommender, RecommendType
from core.fund_pool_live import LIVE_FUND_POOL, ALL_LIVE_POOL

app = Flask(__name__, template_folder='templates')
DATA_DIR = Path(__file__).parent.parent / 'data'
ACTUAL_NAV_FILE = DATA_DIR / 'actual_navs.json'
mgr = HoldingsManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/holdings')
def api_holdings():
    holdings = mgr.list()
    result = []
    actual_navs = {}
    if ACTUAL_NAV_FILE.exists():
        with open(ACTUAL_NAV_FILE, 'r', encoding='utf-8') as f:
            actual_navs = json.load(f)
    
    for h in holdings:
        code = h['code']
        quote = get_realtime_quote(code)
        if not quote:
            continue
        
        cost = float(h.get('cost') or 0)
        shares = float(h.get('shares') or 0)
        
        # 昨净值/昨涨跌：从 actual_navs.json 读取（上一交易日收盘数据，每日19:00-21:00更新）
        act = actual_navs.get(code, {})
        yesterday_nav = act.get('nav', 0)  # 上一交易日收盘净值
        yesterday_chg = act.get('daily_return', 0)  # 上一交易日涨跌幅
        
        # 今净值/今涨跌：从实时API读取（盘中实时估算值，收盘后变成实际值）
        est_nav = quote.get('estimated_nav', 0)  # 今日估算净值
        change_pct = quote.get('change_pct', 0)  # 今日估算涨跌幅
        
        # 当前净值：优先用估算净值（盘中实时），actual_navs 仅用于昨净值参考
        current_nav = est_nav
        
        # 盈亏计算：以今日估值为参考
        profit = (current_nav - cost) * shares if cost > 0 else 0
        profit_pct = ((current_nav - cost) / cost * 100) if cost > 0 else 0
        
        result.append({
            'id': h.get('id'),
            'code': code,
            'name': h.get('name') or code,
            'shares': shares,
            'cost': cost,
            'note': h.get('note') or '',
            'yesterday_nav': yesterday_nav,
            'yesterday_chg': yesterday_chg,
            'current_nav': current_nav,
            'change_pct': change_pct,
            'amount': round(current_nav * shares, 2),
            'profit': round(profit, 2),
            'profit_pct': round(profit_pct, 2),
        })
    return jsonify({'data': result, 'success': True})

@app.route('/api/holdings', methods=['POST'])
def api_holdings_add():
    data = request.get_json() or {}
    code = data.get('code', '')
    name = data.get('name', '')
    shares = float(data.get('shares', 0))
    cost = float(data.get('cost', 0))
    
    if mgr.add(code, name, shares, cost):
        return jsonify({'success': True, 'message': f'已添加 {name or code}'})
    return jsonify({'success': False, 'message': '添加失败或已存在'})

@app.route('/api/holdings/<code>', methods=['PUT'])
def api_holdings_update(code):
    data = request.get_json() or {}
    success = mgr.update(code, **data)
    return jsonify({'success': success})

@app.route('/api/holdings/<code>', methods=['DELETE'])
def api_holdings_delete(code):
    success = mgr.remove(code)
    return jsonify({'success': success, 'message': '删除成功' if success else '删除失败'})

@app.route('/api/fund/<code>')
def api_fund(code):
    quote = get_realtime_quote(code)
    nav_list = get_historical_nav(code, 90)
    return jsonify({'success': True, 'quote': quote, 'nav_list': nav_list})

@app.route('/api/analyze/<code>')
def api_analyze(code):
    """增强版AI量化分析"""
    try:
        from core.enhanced_analyzer import generate_comprehensive_analysis
        
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
            # 自动推送到飞书群
            try:
                from core.feishu_pusher import push_to_feishu
                push_to_feishu(
                    code=code,
                    name=result.get('name', code),
                    ai_report=result.get('ai_report', ''),
                    holding_info=holding_info
                )
            except Exception as e:
                print(f'飞书推送失败: {e}')
            return jsonify({'success': True, 'data': result})
        else:
            return jsonify({'success': False, 'error': result.get('error', '分析失败')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recommend')
def api_recommend():
    rec_type = request.args.get('type', 'momentum')
    category = request.args.get('category', 'all')
    limit = int(request.args.get('limit', 9))
    
    recommender = SmartRecommender()
    
    # 使用动态基金池（从东方财富获取的热门ETF）
    category_map = {
        'all': '全部',
        'broad_index': '宽基指数',
        'industry': '行业',
        'qdii': '全部',
        'commodity': '商品',
        'bond': '全部',
    }
    pool_key = category_map.get(category, '全部')
    all_funds = LIVE_FUND_POOL.get(pool_key, ALL_LIVE_POOL)
    
    # 排除已持仓
    holdings = mgr.list()
    exclude = [h['code'] for h in holdings]
    fund_list = list(all_funds.keys())
    
    rt_map = {'momentum': RecommendType.MOMENTUM, 'contrarian': RecommendType.CONTRARIAN, 
              'low_vol': RecommendType.LOW_VOLATILITY, 'high_sharpe': RecommendType.HIGH_SHARPE,
              'diversify': RecommendType.DIVERSIFICATION}
    
    results = recommender.recommend(fund_list, all_funds, exclude, 
                                    rt_map.get(rec_type, RecommendType.MOMENTUM), limit,
                                    get_historical_nav)
    
    return jsonify({
        'success': True, 
        'data': results, 
        'total_candidates': len(fund_list),
        'pool_update_time': '自动每日更新',
    })

@app.route('/api/recommend/portfolio')
def api_portfolio():
    recommender = SmartRecommender()
    holdings = mgr.list()
    
    if not holdings:
        return jsonify({'success': False, 'message': '请先添加持仓'})
    
    results = recommender.get_portfolio_analysis(holdings, get_historical_nav)
    return jsonify({'success': True, 'data': results})

@app.route('/api/recommend/similar')
def api_similar():
    code = request.args.get('code', '')
    limit = int(request.args.get('limit', 5))
    
    recommender = SmartRecommender()
    all_funds = {**BROAD_INDEX_FUNDS, **INDUSTRY_FUNDS, **BOND_FUNDS, **QDII_FUNDS}
    holdings = mgr.list()
    exclude = [h['code'] for h in holdings]
    
    # 手动实现查找相似基金
    target_nav = get_historical_nav(code, 180)
    if len(target_nav) < 30:
        return jsonify({'success': True, 'data': []})
    
    results = []
    for fc in list(all_funds.keys())[:20]:
        if fc == code or fc in exclude:
            continue
        nav_list = get_historical_nav(fc, 180)
        if len(nav_list) >= 30:
            metrics = recommender.calculate_metrics(fc, all_funds.get(fc, fc), nav_list)
            results.append({
                'code': fc,
                'name': all_funds.get(fc, fc),
                'volatility': round(metrics.volatility * 100, 2),
                'sharpe_ratio': round(metrics.sharpe_ratio, 2),
            })
    
    return jsonify({'success': True, 'data': results[:limit]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
