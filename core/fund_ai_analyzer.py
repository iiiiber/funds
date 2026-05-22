#!/usr/bin/env python3
"""
AI基金分析模块 - MiniMax M2.7 API
"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.fund_analyzer import FundAnalyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


class MiniMaxAI:
    """MiniMax M2.7 API接口"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.api_url = "https://api.minimaxi.com/anthropic/v1/messages"
        self.model = "MiniMax-M2.7-highspeed"
    
    def chat(self, messages: list, temperature: float = 0.5) -> Optional[str]:
        """调用MiniMax M2.7 API"""
        import requests
        
        if not self.api_key:
            logger.warning("未配置MiniMax API Key")
            return None
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        # 构建prompt
        prompt = messages[-1].get('content', '') if messages else ''
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 200
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('content', [])
                for item in content:
                    if item.get('type') == 'text':
                        return item.get('text', '').strip()
                logger.warning("API响应无text内容")
                return None
            else:
                logger.error(f"MiniMax API错误: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"MiniMax请求失败: {e}")
            return None


class FundAIAnalyzer:
    """AI基金分析器"""
    
    def __init__(self, api_key: str = None):
        self.fund_analyzer = FundAnalyzer()
        self.ai = MiniMaxAI(api_key=api_key)
    
    def _get_technical_indicators(self, hist: list) -> Dict:
        """计算技术指标"""
        if len(hist) < 20:
            return {}
        
        prices = [h['nav'] for h in hist]
        
        ma5 = sum(prices[-5:]) / 5
        ma10 = sum(prices[-10:]) / 10
        ma20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else ma10
        
        if prices[-1] > ma5 > ma10 > ma20:
            trend = "上升趋势"
        elif prices[-1] < ma5 < ma10 < ma20:
            trend = "下降趋势"
        elif ma5 > ma10:
            trend = "震荡偏上"
        else:
            trend = "震荡偏下"
        
        momentum_5d = (prices[-1] - prices[-5]) / prices[-5] * 100 if len(prices) >= 5 else 0
        
        return {
            'trend': trend,
            'ma5': round(ma5, 4),
            'ma10': round(ma10, 4),
            'ma20': round(ma20, 4),
            'momentum_5d': round(momentum_5d, 2)
        }
    
    def _generate_recommendation(self, metrics: Dict) -> tuple:
        """生成操作建议"""
        ret_1m = metrics.get('return_1m', 0)
        sharpe = metrics.get('sharpe_6m', 0)
        max_dd = metrics.get('max_drawdown', 0)
        drop = metrics.get('drop_from_high', 0)
        
        score = 0
        
        if 5 < ret_1m < 12:
            score += 20
        elif 0 < ret_1m <= 5:
            score += 10
        elif ret_1m > 15:
            score -= 10
        
        if sharpe > 1.5:
            score += 20
        elif sharpe > 1:
            score += 10
        
        if max_dd < 10:
            score += 15
        elif max_dd < 15:
            score += 10
        
        if -20 < drop < -5:
            score += 15
        elif drop >= 0:
            score -= 10
        
        if score >= 60:
            return "⭐ 建议买入/加仓", score
        elif score >= 40:
            return "📊 建议持有", score
        elif score >= 25:
            return "📉 建议减仓", score
        else:
            return "⚠️ 建议卖出/观望", score
    
    def _generate_rule_report(self, data: Dict) -> str:
        """基于规则生成分析报告"""
        ret_1m = data.get('return_1m', 0)
        sharpe = data.get('sharpe', 0)
        trend = data.get('trend', '未知')
        drop = data.get('drop_from_high', 0)
        recommendation = data.get('recommendation', '持有')
        
        parts = []
        
        if trend in ['上升趋势', '震荡偏上']:
            parts.append(f"技术面{trend}，短期走势较强。")
        elif trend in ['下降趋势', '震荡偏下']:
            parts.append(f"技术面{trend}，短期偏弱，关注是否企稳。")
        else:
            parts.append(f"技术面{trend}，方向待确认。")
        
        reasons = []
        if ret_1m > 5:
            reasons.append("近期表现强劲")
        elif ret_1m < -5:
            reasons.append("近期有所回调")
        if sharpe > 1.5:
            reasons.append("风险收益比优秀")
        if -20 < drop < -5:
            reasons.append("当前价位适中")
        
        if reasons:
            parts.append("主要看点：" + "、".join(reasons[:2]) + "。")
        
        advice = {
            "⭐ 建议买入/加仓": "当前性价比较高，可考虑适当配置。",
            "📊 建议持有": "建议保持当前仓位，谨慎操作。",
            "📉 建议减仓": "建议适当减仓，控制风险。",
            "⚠️ 建议卖出/观望": "建议考虑卖出或观望等待。"
        }
        parts.append(advice.get(recommendation, "建议谨慎操作。"))
        
        return " ".join(parts)
    
    def _generate_ai_report(self, data: Dict) -> Optional[str]:
        """使用MiniMax AI生成报告"""
        prompt = f"""作为专业基金分析师，请根据以下数据给出简洁分析（60字内）：

基金: {data['name']} ({data['code']})
近1月: {data['return_1m']:+.1f}% | 近3月: {data['return_3m']:+.1f}%
夏普比率: {data['sharpe']:.2f} | 最大回撤: {data['max_drawdown']:.1f}%
趋势: {data['trend']}

请用2-3句话给出：1)技术面简析 2)操作建议 3)风险提示。"""
        
        logger.info(f"调用MiniMax AI分析: {data['code']}")
        result = self.ai.chat([{"role": "user", "content": prompt}])
        
        if result:
            logger.info(f"MiniMax AI生成成功: {data['code']}")
        
        return result
    
    def analyze(self, code: str) -> Optional[Dict]:
        """分析单只基金"""
        logger.info(f"开始AI分析: {code}")
        
        metrics = self.fund_analyzer.get_fund_metrics(code, days=90)
        if not metrics:
            return None
        
        name = metrics.get('name', code)
        hist = metrics.get('hist', [])
        
        tech = self._get_technical_indicators(hist)
        recommendation, score = self._generate_recommendation(metrics)
        
        analysis_data = {
            'code': code,
            'name': name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'return_1m': metrics.get('return_1m', 0),
            'return_3m': metrics.get('return_3m', 0),
            'sharpe': metrics.get('sharpe_6m', 0),
            'max_drawdown': metrics.get('max_drawdown', 0),
            'volatility': metrics.get('volatility_3m', 0),
            'drop_from_high': metrics.get('drop_from_high', 0),
            'trend': tech.get('trend', '未知'),
            'recommendation': recommendation,
            'score': score,
        }
        
        # 尝试AI生成
        ai_report = self._generate_ai_report(analysis_data)
        if not ai_report:
            ai_report = self._generate_rule_report(analysis_data)
            logger.info(f"使用规则生成报告: {code}")
        
        analysis_data['ai_report'] = ai_report
        
        logger.info(f"分析完成: {name}, 评分: {score}")
        
        return analysis_data


def analyze_fund(code: str, api_key: str = None) -> Optional[Dict]:
    """快速分析接口"""
    analyzer = FundAIAnalyzer(api_key=api_key)
    return analyzer.analyze(code)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('code', help='基金代码')
    args = parser.parse_args()
    
    result = analyze_fund(args.code)
    
    if result:
        print(f"\n📊 {result['name']} ({result['code']})")
        print(f"🎯 评分: {result['score']}/100 | {result['recommendation']}")
        print(f"💬 {result['ai_report']}")
    else:
        print("分析失败")
