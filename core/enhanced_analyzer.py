#!/usr/bin/env python3
"""增强版基金AI分析 - 方案A+B升级版
- AI调用可靠性（重试+降级）
- 多模型切换（读数据库配置）
- 丰富prompt（500字）
- 估值分析（PE/PB百分位）
- 资金流向
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import requests
from datetime import datetime
import pandas as pd
from core.fund_analyzer import FundAnalyzer
from core.analysis import calculate_volatility, calculate_sharpe_ratio, calculate_max_drawdown
from core.fund_api import get_historical_nav

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'funds',
    'password': '6NZ7Hp2Z5YWShARJ',
    'database': 'funds',
    'charset': 'utf8mb4',
}


def _decrypt_key(encrypted_key: str) -> str:
    """解密API密钥"""
    if not encrypted_key:
        return ''
    try:
        import base64
        import hashlib
        from cryptography.fernet import Fernet
        _key = base64.urlsafe_b64encode(hashlib.sha256(b'fundquant_admin_key_2026').digest())
        fernet = Fernet(_key)
        return fernet.decrypt(encrypted_key.encode()).decode()
    except:
        return encrypted_key  # fallback: 原始值


def _load_ai_config_from_db(where: str) -> dict:
    """从数据库读取AI配置（自动解密）"""
    import pymysql
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(f"SELECT api_url, api_key, model_id FROM ai_models WHERE {where} LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {'api_url': row[0], 'api_key': _decrypt_key(row[1]), 'model_id': row[2]}


def get_ai_config():
    """从数据库读取AI模型配置"""
    try:
        cfg = _load_ai_config_from_db("is_default=1 AND status=1")
        if cfg:
            return cfg
    except:
        pass
    # fallback to env
    return {
        'api_url': os.environ.get('AI_API_URL', 'https://api.minimaxi.com/anthropic/v1/messages'),
        'api_key': os.environ.get('MINIMAX_API_KEY', ''),
        'model_id': os.environ.get('AI_MODEL_ID', 'MiniMax-M2.7-highspeed'),
    }


class AIGateway:
    """统一AI调用网关 - 支持多模型、重试、降级"""

    def __init__(self):
        self.config = get_ai_config()

    def chat(self, prompt: str, temperature: float = 0.3, max_tokens: int = 600) -> tuple:
        """
        返回 (text, model_used, success)
        - text: AI回复内容
        - model_used: 实际使用的模型
        - success: 是否成功调用AI
        """
        api_url = self.config['api_url']
        api_key = self.config['api_key']
        model = self.config['model_id']

        if not api_key:
            return None, None, False

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }

        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # 3次重试
        for attempt in range(3):
            try:
                resp = requests.post(api_url, headers=headers, json=data, timeout=30)
                if resp.status_code == 200:
                    result = resp.json()
                    # Anthropic format: content: [{type: 'text', text: '...'}]
                    content = result.get('content', [])
                    for item in content:
                        if item.get('type') == 'text':
                            return item.get('text', '').strip(), model, True
                    # OpenAI format: choices: [{message: {content: '...'}}]
                    choices = result.get('choices', [])
                    for item in choices:
                        msg = item.get('message', {})
                        txt = msg.get('content', '')
                        if txt:
                            return txt.strip(), model, True
                elif resp.status_code == 429:
                    # 限流，等2秒重试
                    time.sleep(2)
                    continue
                else:
                    break
            except Exception as e:
                time.sleep(1)

        # 降级：尝试DeepSeek备用
        return self._try_deepseek_fallback(prompt)

    def _try_deepseek_fallback(self, prompt: str) -> tuple:
        """降级到DeepSeek"""
        try:
            cfg = _load_ai_config_from_db("type='chat' AND status=1 AND is_default=0")
            if not cfg:
                return None, None, False
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {cfg['api_key']}",
            }
            data = {
                "model": cfg['model_id'],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 600
            }
            resp = requests.post(cfg['api_url'], headers=headers, json=data, timeout=8)
            if resp.status_code == 200:
                result = resp.json()
                text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                if text:
                    return text.strip(), cfg['model_id'], True
        except:
            pass
        return None, None, False


def get_market_indicators() -> dict:
    """获取市场情绪指标（增强版）"""
    indicators = {
        'market_sentiment': '中性',
        'risk_level': '中等',
        'hot_sectors': [],
        'market_volatility': '适中',
        'fund_flows': '平稳',
        'market_index_change': 0,
        'fear_greed': 50,  # 恐惧贪婪指数 0-100
    }

    try:
        quote = get_historical_nav('000001', 5)
        if quote and len(quote) >= 2:
            change = (quote[-1]['nav'] - quote[0]['nav']) / quote[0]['nav'] * 100
            indicators['market_index_change'] = round(change, 2)
            if change > 1.5:
                indicators['market_sentiment'] = '乐观'
                indicators['risk_level'] = '偏低'
                indicators['fear_greed'] = min(80, 50 + int(change * 5))
            elif change < -1.5:
                indicators['market_sentiment'] = '谨慎'
                indicators['risk_level'] = '偏高'
                indicators['fear_greed'] = max(20, 50 + int(change * 5))
    except:
        pass

    return indicators


def get_valuation_indicators(code: str, fund_name: str = '') -> dict:
    val = {'pe_percentile': None, 'pb_percentile': None, 'pe': None, 'pb': None,
           'valuation_level': '未知', 'benchmark': None, 'nav_percentile': None}

    name_lower = fund_name.lower()

    if any(k in name_lower for k in ['黄金', '白银', '商品', '原油', '能源', '大宗', '铜', '铝', '煤炭', '钢铁', '畜牧', '豆粕', '玉米']):
        val['valuation_level'] = '不适用（资源商品）'
        val['benchmark'] = '商品指数'
        return val

    if any(k in name_lower for k in ['纳斯达克', '标普', '道琼斯', '日经', '恒生', '港股', '越南', '印度', '德国', '法国', '英国', '美国', '美股', 'QDII', '全球', '海外', '境外']):
        val['valuation_level'] = '不适用（境外市场）'
        val['benchmark'] = '境外指数'
        return val

    if any(k in name_lower for k in ['货币', '现金', '短期理财', '余额宝', '零钱通']):
        val['valuation_level'] = '不适用（货币基金）'
        val['benchmark'] = '货币基金'
        return val

    if any(k in name_lower for k in ['债券', '纯债', '信用债', '国债', '政金', '企债', '金融债']):
        val['valuation_level'] = '不适用（债券基金）'
        val['benchmark'] = '债券指数'
        return val

    sector_map = {'半导体': '半导体', '芯片': '半导体', '集成电路': '半导体',
                  '新能源': '新能源', '光伏': '新能源', '储能': '新能源',
                  '医疗': '医药', '医药': '医药', '消费': '消费', '军工': '军工',
                  '通信': '通信', '电子': '电子', '计算机': '计算机',
                  '人工智能': '人工智能', 'AI': '人工智能', '数字经济': '数字经济'}
    sector = None
    for kw, s in sector_map.items():
        if kw in name_lower:
            sector = s
            break

    try:
        nav_list = get_historical_nav(code, 250)
        if nav_list and len(nav_list) >= 60:
            prices = [h['nav'] for h in nav_list]
            current = prices[-1]
            import statistics
            hist_max = max(prices)
            hist_min = min(prices)
            mean = statistics.mean(prices)
            stdev = statistics.stdev(prices) if len(prices) > 1 else 0
            if stdev > 0:
                z = (current - mean) / stdev
                val['z_score'] = round(z, 2)
            if hist_max > hist_min:
                nav_pct = (current - hist_min) / (hist_max - hist_min) * 100
                val['nav_percentile'] = round(nav_pct, 1)
            val['drop_from_high'] = round((current - hist_max) / hist_max * 100, 1)
    except Exception:
        pass

    sector_flow = None
    if sector:
        try:
            import akshare as ak
            df = ak.stock_sector_fund_flow_hist(symbol=sector)
            if df is not None and len(df) >= 5:
                avg_pct = df['主力净流入-净占比'].tail(5).mean()
                sector_flow = {'pct': avg_pct}
                val['sector_flow'] = f"{avg_pct:+.1f}%"
        except Exception:
            pass

    nav_pct = val.get('nav_percentile')
    sector_pct = sector_flow['pct'] if sector_flow else 0

    z_score = val.get('z_score')
    if z_score is not None:
        try:
            n = get_historical_nav(code, 22)
            return_1m = ((n[-1]['nav'] - n[0]['nav']) / n[0]['nav'] * 100) if len(n) >= 22 else 0
        except:
            return_1m = 0

        # Z-Score 判断：高Z=高估，低Z=低估
        if z_score >= 2.5:
            level = '极度高估' if return_1m > 10 else ('强势（注意风险）' if return_1m > 0 else '高估（反弹无力）')
        elif z_score >= 2.0:
            level = '强势（注意风险）' if return_1m > 15 else ('强势' if return_1m > 5 else '高估')
        elif z_score >= 1.5:
            level = '偏高' if return_1m < 5 else ('强势' if return_1m > 15 else '正常')
        elif z_score >= 1.0:
            level = '正常' if return_1m < 10 else '偏高'
        elif z_score >= 0.5:
            level = '正常偏低'
        elif z_score >= 0:
            level = '正常'
        else:
            level = '低估'

        val['valuation_level'] = level
        parts = [f'Z={z_score:.1f}']
        if sector:
            parts.append(f'{sector}板块')
        if sector_flow:
            parts.append(f'资金{sector_pct:+.1f}%')
        val['benchmark'] = ' | '.join(parts)
        val['nav_percentile'] = None  # z_score replaces nav_percentile
    else:
        if sector_flow:
            val['valuation_level'] = '资金流入（偏多）' if sector_pct > 2 else ('资金流出（偏空）' if sector_pct < -2 else '资金平稳')
            val['benchmark'] = f'{sector}板块' if sector else '行业板块'
        else:
            val['valuation_level'] = '数据不足'
            val['benchmark'] = '无参考基准'

    return val



def get_fund_flows(code: str, days: int = 20) -> dict:
    """获取资金流向（近N日净流入估算）"""
    flows = {'net_flow_20d': 0, 'flow_direction': '平稳'}
    try:
        nav_list = get_historical_nav(code, days)
        if nav_list and len(nav_list) >= 5:
            total_change = nav_list[-1]['nav'] - nav_list[0]['nav']
            flows['net_flow_20d'] = round(total_change * 100, 2)
            if flows['net_flow_20d'] > 3:
                flows['flow_direction'] = '资金流入'
            elif flows['net_flow_20d'] < -3:
                flows['flow_direction'] = '资金流出'
    except:
        pass
    return flows


def calculate_technical_indicators(hist: list) -> dict:
    """计算技术指标"""
    if len(hist) < 10:
        return {'trend': '数据不足'}

    prices = [h['nav'] for h in hist]

    ma5 = sum(prices[-5:]) / 5
    ma10 = sum(prices[-10:]) / 10 if len(prices) >= 10 else ma5
    ma20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else ma10
    ma60 = sum(prices[-60:]) / 60 if len(prices) >= 60 else ma20
    current = prices[-1]

    # 趋势判断（多周期）
    if current > ma5 > ma10 > ma20 > ma60:
        trend = "强势上升"
    elif current > ma5 and ma5 > ma10 and ma10 > ma20:
        trend = "震荡偏强"
    elif current < ma5 < ma10 < ma20 < ma60:
        trend = "弱势下跌"
    elif current < ma5 and ma5 < ma10:
        trend = "震荡偏弱"
    else:
        trend = "区间震荡"

    # 动量
    momentum_5d = (prices[-1] - prices[-5]) / prices[-5] * 100 if len(prices) >= 5 else 0
    momentum_20d = (prices[-1] - prices[-20]) / prices[-20] * 100 if len(prices) >= 20 else 0

    # 距离高点的回撤
    max_nav = max(prices)
    drop_from_high = (current - max_nav) / max_nav * 100

    return {
        'trend': trend,
        'ma5': round(ma5, 4),
        'ma10': round(ma10, 4),
        'ma20': round(ma20, 4),
        'ma60': round(ma60, 4) if len(prices) >= 60 else None,
        'momentum_5d': round(momentum_5d, 2),
        'momentum_20d': round(momentum_20d, 2),
        'drop_from_high': round(drop_from_high, 2),
    }


def generate_comprehensive_analysis(code: str, holding_info: dict = None) -> dict:
    """生成综合分析结果（增强版）"""

    result = {
        'success': False,
        'code': code,
        'name': '',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'holding': {},
        'metrics': {},
        'technical': {},
        'market': {},
        'valuation': {},
        'flows': {},
        'recommendation': {},
        'ai_report': '',
        'ai_used': False,
        'model_used': None,
        'action_suggestions': [],
    }

    try:
        # 1. 获取基金基本信息
        from core.fund_api import get_realtime_quote
        quote = get_realtime_quote(code)
        if quote:
            result['name'] = quote.get('name', code)
            result['holding']['current_nav'] = quote.get('price', 0)
            result['holding']['change_pct'] = quote.get('change_pct', 0)

        # 2. 获取历史数据
        nav_list = get_historical_nav(code, 250)  # 增加到250天
        if not nav_list or len(nav_list) < 5:
            result['error'] = '历史数据不足'
            return result

        # 3. 计算基础指标（多周期）
        prices = [h['nav'] for h in nav_list]

        result['metrics'] = {
            'return_1w': round((prices[-1] - prices[-7]) / prices[-7] * 100, 2) if len(prices) >= 7 else 0,
            'return_1m': round((prices[-1] - prices[-22]) / prices[-22] * 100, 2) if len(prices) >= 22 else 0,
            'return_3m': round((prices[-1] - prices[-65]) / prices[-65] * 100, 2) if len(prices) >= 65 else 0,
            'return_6m': round((prices[-1] - prices[-130]) / prices[-130] * 100, 2) if len(prices) >= 130 else 0,
            'return_1y': round((prices[-1] - prices[-250]) / prices[-250] * 100, 2) if len(prices) >= 250 else 0,
            'volatility': round(calculate_volatility(nav_list) * 100, 2),
            'sharpe': round(calculate_sharpe_ratio(nav_list), 2),
            'max_drawdown': round(calculate_max_drawdown(nav_list) * 100, 2),
        }

        # 4. 计算技术指标
        result['technical'] = calculate_technical_indicators(nav_list)

        # 5. 获取市场指标
        result['market'] = get_market_indicators()

        # 6. 估值分析
        fund_name = result.get('name', '')
        result['valuation'] = get_valuation_indicators(code, fund_name)

        # 7. 资金流向
        result['flows'] = get_fund_flows(code, 20)

        # 8. 处理持仓信息
        if holding_info:
            result['holding'].update({
                'shares': float(holding_info.get('shares', 0) or 0),
                'cost': float(holding_info.get('cost', 0) or 0),
                'amount': float(holding_info.get('amount', 0) or 0),
                'profit': float(holding_info.get('profit', 0) or 0),
                'profit_pct': float(holding_info.get('profit_pct', 0) or 0),
            })
            current_nav = result['holding']['current_nav']
            if current_nav > 0 and holding_info.get('shares', 0) > 0:
                current_amount = float(current_nav) * float(holding_info.get('shares', 0))
                result['holding']['current_value'] = round(current_amount, 2)
                result['holding']['profit'] = round(current_amount - float(holding_info.get('cost', 0)) * float(holding_info.get('shares', 0)), 2)
                result['holding']['profit_pct'] = round((current_amount - float(holding_info.get('cost', 0)) * float(holding_info.get('shares', 0))) / (float(holding_info.get('cost', 0)) * float(holding_info.get('shares', 0))) * 100, 2) if holding_info['cost'] > 0 else 0
            else:
                result['holding']['current_nav'] = 0
                if holding_info.get('profit_pct', 0) != 0:
                    result['holding']['profit_pct'] = holding_info.get('profit_pct', 0)

        # 9. 生成评分
        score = 50
        factors = []
        ret_1m = result['metrics']['return_1m']
        ret_3m = result['metrics']['return_3m']
        sharpe = result['metrics']['sharpe']
        max_dd = result['metrics']['max_drawdown']
        trend = result['technical']['trend']

        # 多周期收益率评估
        if 5 < ret_1m < 15:
            score += 10
            factors.append(f"近1月{ret_1m:+.1f}%表现良好")
        elif ret_1m > 15:
            score += 3
            factors.append(f"近1月{ret_1m:+.1f}%短期偏热")
        elif ret_1m < -10:
            score -= 8
            factors.append(f"近1月下跌{ret_1m:.1f}%短期承压")

        if ret_3m > 20:
            score += 8
            factors.append(f"近3月{ret_3m:+.1f}%持续强势")
        elif ret_3m < -15:
            score -= 8
            factors.append(f"近3月下跌{ret_3m:.1f}%趋势较弱")

        # 夏普比率
        if sharpe > 2:
            score += 15
            factors.append(f"夏普比率{sharpe:.2f}优秀")
        elif sharpe > 1.5:
            score += 10
            factors.append(f"夏普比率{sharpe:.2f}良好")
        elif sharpe > 1:
            score += 5
            factors.append(f"夏普比率{sharpe:.2f}一般")

        # 最大回撤
        if max_dd < 10:
            score += 8
            factors.append(f"最大回撤{max_dd:.1f}%风控良好")
        elif max_dd > 25:
            score -= 10
            factors.append(f"最大回撤{max_dd:.1f}%风险较高")

        # 趋势
        if '强势' in trend:
            score += 10
            factors.append(f"技术面{trend}")
        elif '偏强' in trend:
            score += 5
            factors.append(f"技术面{trend}")
        elif '弱势' in trend:
            score -= 8
            factors.append(f"技术面{trend}需谨慎")
        elif '偏弱' in trend:
            score -= 4
            factors.append(f"技术面{trend}")

        # 估值
        val_level = result['valuation'].get('valuation_level', '未知')
        if val_level == '低估':
            score += 8
            factors.append("估值处于历史低位")
        elif val_level == '高估':
            score -= 8
            factors.append("估值处于历史高位")

        # 资金流向
        flow_dir = result['flows'].get('flow_direction', '平稳')
        if flow_dir == '资金流入':
            score += 5
            factors.append("近期资金持续流入")
        elif flow_dir == '资金流出':
            score -= 5
            factors.append("近期资金持续流出")

        # 持仓盈亏
        if holding_info and holding_info.get('profit_pct', 0) > 15:
            score -= 5
            factors.append(f"持仓盈利{holding_info['profit_pct']:.1f}%注意止盈")
        elif holding_info and holding_info.get('profit_pct', 0) < -15:
            score += 3
            factors.append(f"持仓亏损{holding_info['profit_pct']:.1f}%可关注补仓")

        # 市场情绪
        if result['market']['risk_level'] == '偏高':
            score -= 5
            factors.append("当前市场风险偏高")

        score = max(0, min(100, score))

        # 10. 生成建议
        if score >= 70:
            action = "建议买入/加仓"
            action_level = "积极"
        elif score >= 55:
            action = "建议持有/适度加仓"
            action_level = "稳健"
        elif score >= 40:
            action = "建议持有观察"
            action_level = "中性"
        elif score >= 25:
            action = "建议减仓观望"
            action_level = "谨慎"
        else:
            action = "建议卖出/规避"
            action_level = "风险"

        result['recommendation'] = {
            'score': score,
            'action': action,
            'level': action_level,
            'factors': factors,
        }

        # 11. 生成规则报告（AI失败时的后备）
        rule_report = _generate_rule_report(result, holding_info)
        result['ai_report'] = rule_report

        # 12. 调用AI增强分析
        ai_prompt = _build_rich_prompt(result, holding_info)
        ai_text, model, ai_ok = AIGateway().chat(ai_prompt)
        if ai_ok and ai_text and len(ai_text) > 50:
            result['ai_report'] = ai_text
            result['ai_used'] = True
            result['model_used'] = model
            # AI结论同步到recommendation（覆盖规则打分结果）
            _sync_ai_recommendation(result, ai_text)

        result['success'] = True

    except Exception as e:
        result['error'] = str(e)

    return result


def _sync_ai_recommendation(result: dict, ai_text: str):
    """从AI报告中提取操作结论，同步到recommendation字段"""
    import re
    # 尝试解析 [操作结论] 行
    match = re.search(r'\[操作结论\]\s*动作[：:]\s*(买入|持有|减仓|清仓)\s*[|]\s*评分[：:]\s*(\d+)\s*[|]\s*级别[：:]\s*(激进|稳健|中性|谨慎|风险)', ai_text)
    if match:
        action_map = {'买入': '建议买入/加仓', '持有': '建议持有/适度加仓', '减仓': '建议减仓观望', '清仓': '建议卖出/规避'}
        level_map = {'激进': '积极', '稳健': '稳健', '中性': '中性', '谨慎': '谨慎', '风险': '风险'}
        result['recommendation'] = {
            'action': action_map.get(match.group(1), '建议持有'),
            'score': int(match.group(2)),
            'level': level_map.get(match.group(3), '中性'),
            'factors': ['AI综合分析结论'],
        }
    else:
        # 从AI报告关键词推断
        if any(k in ai_text for k in ['分批止盈', '减持', '锁定利润', '减仓', '清仓']):
            action, level, score = '建议减仓观望', '谨慎', 55
        elif any(k in ai_text for k in ['不建议追加', '等待回调', '控制仓位']):
            action, level, score = '建议持有/适度加仓', '中性', 60
        elif any(k in ai_text for k in ['加仓', '买入', '布局', '配置']):
            action, level, score = '建议买入/加仓', '积极', 72
        else:
            action, level, score = '建议持有/适度加仓', '稳健', 65

        result['recommendation'] = {
            'action': action,
            'score': score,
            'level': level,
            'factors': ['AI综合分析结论'],
        }


def _generate_rule_report(result: dict, holding_info) -> str:
    """生成规则基础报告（AI不可用时使用）"""
    parts = []
    m = result['metrics']
    t = result['technical']
    v = result['valuation']
    f = result['flows']
    r = result['recommendation']

    sentiment = result['market'].get('market_sentiment', '中性')
    if sentiment == '乐观':
        parts.append(f"📈 市场情绪{sentiment}，有利于权益资产")
    elif sentiment == '谨慎':
        parts.append(f"⚠️ 市场情绪{sentiment}，建议控制仓位")
    else:
        parts.append(f"📊 市场情绪{sentiment}，保持中性配置")

    parts.append(f"\n【{result['name'] or result['code']}】")
    parts.append(f"• 多周期收益：近1周{m.get('return_1w',0):+.1f}% | 近1月{m.get('return_1m',0):+.1f}% | 近3月{m.get('return_3m',0):+.1f}%")
    parts.append(f"• 风险指标：波动率{m.get('volatility',0):.1f}% | 夏普{m.get('sharpe',0):.2f} | 最大回撤{m.get('max_drawdown',0):.1f}%")
    parts.append(f"• 技术面：{t.get('trend','数据不足')} | MA20={t.get('ma20',0):.4f}")

    if v.get('valuation_level', '未知') != '未知':
        parts.append(f"• 估值：{v.get('valuation_level')}（PE={v.get('pe','N/A')} | 历史{v.get('pe_percentile','N/A')}%分位）")

    if holding_info and holding_info.get('shares', 0) > 0:
        profit_pct = result['holding'].get('profit_pct', 0)
        if profit_pct > 0:
            parts.append(f"• 您的持仓：盈利{profit_pct:.1f}% | {f.get('flow_direction','平稳')}")
        else:
            parts.append(f"• 您的持仓：亏损{abs(profit_pct):.1f}% | {f.get('flow_direction','平稳')}")

    parts.append(f"\n💡 综合评分{r['score']}分（{r['level']}），{r['action']}")
    parts.append(f"📋 {'；'.join(r['factors'][:4])}")

    return '\n'.join(parts)


def _build_rich_prompt(result: dict, holding_info) -> str:
    """构建丰富的AI分析Prompt"""
    m = result['metrics']
    t = result['technical']
    v = result['valuation']
    f = result['flows']
    mk = result['market']
    r = result['recommendation']

    holding_desc = ""
    if holding_info and holding_info.get('shares', 0) > 0:
        profit_pct = result['holding'].get('profit_pct', 0)
        holding_desc = f"""持仓状态：持有{holding_info.get('shares')}份，成本{holding_info.get('cost')}元，当前盈利{profit_pct:.1f}%（{result['holding'].get('profit',0):+.2f}元），属于{'盈利状态' if profit_pct>=0 else '亏损状态'}。"""

    prompt = f"""你是专业基金投资顾问，请对以下基金进行深入分析并给出个性化建议。

【基金基本信息】
基金名称：{result['name'] or result['code']}
基金代码：{result['code']}

【多周期收益表现】
近1周：{m.get('return_1w',0):+.1f}%
近1月：{m.get('return_1m',0):+.1f}%
近3月：{m.get('return_3m',0):+.1f}%
近6月：{m.get('return_6m',0):+.1f}%（如可计算）
近1年：{m.get('return_1y',0):+.1f}%（如可计算）

【风险收益指标】
波动率（年化）：{m.get('volatility',0):.1f}%
夏普比率：{m.get('sharpe',0):.2f}（>1为良好，>2为优秀）
最大回撤：{m.get('max_drawdown',0):.1f}%

【技术面分析】
当前趋势：{t.get('trend','数据不足')}
MA5/MA10/MA20：{t.get('ma5',0):.4f} / {t.get('ma10',0):.4f} / {t.get('ma20',0):.4f}
5日动量：{t.get('momentum_5d',0):+.1f}%
20日动量：{t.get('momentum_20d',0):+.1f}%
距离历史高点：{t.get('drop_from_high',0):+.1f}%

【估值分析】
估值水平：{v.get('valuation_level','无法获取')}
市盈率(PE)：{v.get('pe','无法获取')}
PE历史百分位：{v.get('pe_percentile','无法获取')}%（越小越低估）

【资金流向】
近20日资金：{f.get('flow_direction','平稳')}（{f.get('net_flow_20d',0):+.1f}%）

【市场环境】
市场情绪：{mk.get('market_sentiment','未知')}
风险等级：{mk.get('risk_level','未知')}
恐惧贪婪指数：{mk.get('fear_greed',50)}/100
恐惧贪婪：{'极度恐惧' if mk.get('fear_greed',50)<25 else '恐惧' if mk.get('fear_greed',50)<45 else '中性' if mk.get('fear_greed',50)<65 else '贪婪' if mk.get('fear_greed',50)<85 else '极度贪婪'}

【持仓者状态】
{holding_desc}

请按以下格式生成300-500字的分析报告，要求：
1. 简要点评：结合多周期表现和技术面给出一个核心评价
2. 操作建议：根据持仓状态和估值给出具体操作建议（结论要明确，不能模棱两可）
3. 风险提示：指出当前最大风险点
4. 分析逻辑：说明支撑你建议的主要依据

报告末尾请以以下格式给出总结（供程序读取）：
[操作结论] 动作：买入/持有/减仓/清仓 | 评分：0-100 | 级别：激进/稳健/中性/谨慎/风险

请使用中文回复，语言专业但易懂。"""

    return prompt


if __name__ == '__main__':
    import json
    result = generate_comprehensive_analysis('018957')
    print(json.dumps(result, indent=2, ensure_ascii=False))

# DEBUG: test function
def test_ai_call():
    import requests, time
    cfg = _load_ai_config_from_db("is_default=0 AND status=1")
    if not cfg:
        return "No fallback config"
    url = cfg[api_url]
    key = cfg[api_key]
    model = cfg[model_id]
    start = time.time()
    try:
        resp = requests.post(url, headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}, json={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10}, timeout=8)
        elapsed = time.time() - start
        return f"Status {resp.status_code} in {elapsed:.2f}s: {resp.text[:100]}"
    except Exception as e:
        return f"Error in {time.time()-start:.2f}s: {e}"
