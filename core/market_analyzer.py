#!/usr/bin/env python3
"""市场分析模块 - 方案B新增
- 板块轮动信号
- 宏观周期判断
- 北向资金
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import requests


def get_sector_rotation() -> dict:
    """
    获取板块轮动信号
    返回当日强势板块和轮动方向
    """
    result = {
        'hot_sectors': [],
        'rotation_direction': '未知',
        'sector_changes': [],
        'market_style': '均衡',  # 成长/价值/均衡
    }

    try:
        import akshare as ak

        # 获取行业板块涨跌
        try:
            df = ak.stock_sector_spot(indicator="涨幅")
            if df is not None and len(df) > 0:
                # 取涨幅前10
                top = df.head(10)
                hot = []
                for _, row in top.iterrows():
                    name = str(row.get('名称', ''))
                    change = row.get('涨跌幅', 0)
                    if name and abs(float(change)) > 0.5:
                        hot.append({'name': name, 'change': float(change)})
                result['hot_sectors'] = hot[:5]

                # 判断轮动方向：科技→消费→金融→周期
                sector_types = {
                    '芯片': '科技', '半导体': '科技', '人工智能': '科技', '软件': '科技', '电子': '科技',
                    '新能源': '成长', '光伏': '成长', '锂电': '成长', '汽车': '成长',
                    '消费': '消费', '食品': '消费', '白酒': '消费', '医药': '消费',
                    '证券': '金融', '银行': '金融', '保险': '金融',
                    '煤炭': '周期', '钢铁': '周期', '有色': '周期', '化工': '周期', '房地产': '周期',
                }
                style_count = {'科技': 0, '成长': 0, '消费': 0, '金融': 0, '周期': 0}
                for s in hot:
                    for kw, style in sector_types.items():
                        if kw in s['name']:
                            style_count[style] += 1
                            break
                dominant = max(style_count, key=style_count.get)
                if style_count[dominant] >= 2:
                    result['market_style'] = dominant
        except:
            pass

        # 获取概念板块
        try:
            df2 = ak.stock_board_concept_name_em()
            if df2 is not None and len(df2) > 0:
                df2['涨跌幅'] = df2['涨跌幅'].astype(float)
                top_concept = df2.nlargest(5, '涨跌幅')
                concepts = []
                for _, row in top_concept.iterrows():
                    concepts.append({
                        'name': str(row.get('板块名称', '')),
                        'change': float(row.get('涨跌幅', 0)),
                        'lead': str(row.get('领先板块', ''))[:30]
                    })
                result['sector_changes'] = concepts
        except:
            pass

        # 备用数据源：新浪财经行业板块（当akshare东方财富接口不可用时）
        if not result['hot_sectors']:
            try:
                from core.sina_backup import get_sina_sectors
                sina_sectors = get_sina_sectors()
                if sina_sectors:
                    # 取涨幅前5
                    hot = [s for s in sina_sectors if s['change'] > 0][:5]
                    result['hot_sectors'] = hot
                    # 判断风格
                    sector_types = {
                        '芯片': '科技', '半导体': '科技', '人工智能': '科技', '软件': '科技', '电子': '科技',
                        '新能源': '成长', '光伏': '成长', '锂电': '成长', '汽车': '成长',
                        '消费': '消费', '食品': '消费', '白酒': '消费', '医药': '消费',
                        '证券': '金融', '银行': '金融', '保险': '金融',
                        '煤炭': '周期', '钢铁': '周期', '有色': '周期', '化工': '周期', '房地产': '周期',
                        '仪器仪表': '制造', '通用设备': '制造', '电气': '制造', '金属制品': '制造',
                    }
                    style_count = {'科技': 0, '成长': 0, '消费': 0, '金融': 0, '周期': 0, '制造': 0}
                    for s in hot:
                        for kw, style in sector_types.items():
                            if kw in s['name']:
                                style_count[style] += 1
                                break
                    dominant = max(style_count, key=style_count.get)
                    if style_count[dominant] >= 1:
                        result['market_style'] = dominant
                    result['rotation_direction'] = '数据来源：新浪财经'
            except Exception:
                pass

    except ImportError:
        result['error'] = 'akshare未安装'
    except Exception as e:
        result['error'] = str(e)

    return result


def get_macro_cycle() -> dict:
    """
    获取宏观周期判断
    - A股情绪
    - 利率环境
    - 北向资金
    """
    result = {
        'cycle_position': '不确定',  # 复苏/扩张/滞胀/衰退
        'a_sentiment': '中性',
        'north_flow_5d': 0,
        'bond_yield_10y': None,
        'risk_level': '中等',
        'cycle_desc': '',
    }

    try:
        import akshare as ak

        # 十年期国债收益率（市场无风险利率）
        try:
            df = ak.bond_zh_us_rate()
            if df is not None and len(df) > 0:
                ten_yr = df[df['期限'] == '美国10年国债收益率']
                if len(ten_yr) > 0:
                    result['bond_yield_10y'] = float(ten_yr['最新价'].iloc[-1])
        except:
            pass

        # 北向资金（沪深港通）
        try:
            north_df = ak.stock_em_hsgt_north_flow(indicator="沪深港通北向5日净流入")
            if north_df is not None and len(north_df) > 0:
                result['north_flow_5d'] = float(north_df.iloc[-1, 1]) if north_df.shape[1] > 1 else 0
        except:
            pass

        # A股情绪（用上证指数波动率简单判断）
        try:
            from core.fund_api import get_historical_nav
            nav = get_historical_nav('000001', 20)
            if nav and len(nav) >= 10:
                prices = [h['nav'] for h in nav]
                changes = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(1, len(prices))]
                avg_vol = sum(abs(c) for c in changes) / len(changes)
                if avg_vol > 1.5:
                    result['a_sentiment'] = '极度活跃'
                    result['risk_level'] = '偏高'
                elif avg_vol > 1.0:
                    result['a_sentiment'] = '活跃'
                    result['risk_level'] = '中等'
                elif avg_vol < 0.5:
                    result['a_sentiment'] = '低迷'
                    result['risk_level'] = '偏低'
                else:
                    result['a_sentiment'] = '平稳'
        except:
            pass

        # 基于利率判断周期（简化版）
        y = result['bond_yield_10y']
        if y:
            if y > 3.5:
                if result['north_flow_5d'] > 50:
                    result['cycle_position'] = '复苏后期'
                    result['cycle_desc'] = '利率偏高但外资持续流入，警惕滞胀风险'
                else:
                    result['cycle_position'] = '滞胀/衰退'
                    result['cycle_desc'] = '高利率环境，经济增长承压'
            elif y > 2.8:
                result['cycle_position'] = '扩张中后期'
                result['cycle_desc'] = '利率适中偏中性，经济温和增长'
            else:
                result['cycle_position'] = '复苏前期'
                result['cycle_desc'] = '低利率环境，政策友好，利于风险资产'

    except ImportError:
        result['error'] = 'akshare未安装'
    except Exception as e:
        result['error'] = str(e)

    return result


def get_fear_greed_index() -> dict:
    """
    简单版恐惧贪婪指数
    基于市场波动率 + 北向资金 + 情绪指标综合打分
    """
    fg = {'index': 50, 'level': '中性', 'signals': []}

    try:
        # 1. 波动率信号
        from core.fund_api import get_historical_nav
        nav = get_historical_nav('000001', 20)
        if nav and len(nav) >= 10:
            prices = [h['nav'] for h in nav]
            changes = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(1, len(prices))]
            vol = sum(abs(c) for c in changes) / len(changes)
            if vol > 2:
                fg['signals'].append(('市场极度波动', -15))
            elif vol > 1.5:
                fg['signals'].append(('市场波动较大', -8))
            elif vol < 0.5:
                fg['signals'].append(('市场平稳', 5))
            else:
                fg['signals'].append(('市场正常波动', 0))

        # 2. 趋势信号
        if nav and len(nav) >= 20:
            ma5 = sum(prices[-5:]) / 5
            ma20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else ma5
            if prices[-1] > ma5 > ma20:
                fg['signals'].append(('均线多头排列', 10))
            elif prices[-1] < ma5 < ma20:
                fg['signals'].append(('均线空头排列', -10))
            else:
                fg['signals'].append(('均线纠缠', 0))

        # 3. 北向资金
        try:
            import akshare as ak
            north = ak.stock_em_hsgt_north_flow(indicator="沪深港通北向5日净流入")
            if north is not None and len(north) > 0:
                flow = float(north.iloc[-1, 1]) if north.shape[1] > 1 else 0
                if flow > 100:
                    fg['signals'].append(('北向大幅净流入', 10))
                elif flow > 30:
                    fg['signals'].append(('北向净流入', 5))
                elif flow < -100:
                    fg['signals'].append(('北向大幅净流出', -10))
                elif flow < -30:
                    fg['signals'].append(('北向净流出', -5))
        except:
            pass

        # 汇总
        base = 50
        for _, delta in fg['signals']:
            base += delta
        fg['index'] = max(0, min(100, base))

        if fg['index'] >= 75:
            fg['level'] = '极度贪婪'
        elif fg['index'] >= 60:
            fg['level'] = '贪婪'
        elif fg['index'] >= 40:
            fg['level'] = '中性'
        elif fg['index'] >= 25:
            fg['level'] = '恐惧'
        else:
            fg['level'] = '极度恐惧'

    except Exception as e:
        fg['error'] = str(e)

    return fg


def get_market_summary() -> dict:
    """综合市场概况 - 供分析接口调用"""
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'sectors': get_sector_rotation(),
        'macro': get_macro_cycle(),
        'fear_greed': get_fear_greed_index(),
    }


if __name__ == '__main__':
    import json
    print(json.dumps(get_market_summary(), indent=2, ensure_ascii=False))
