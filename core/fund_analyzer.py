#!/usr/bin/env python3
"""基金分析核心模块 - 计算收益率、波动率、夏普比率等指标"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.fund_api import get_realtime_quote, get_historical_nav

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


class FundAnalyzer:
    """基金分析器"""

    def __init__(self, risk_free_rate: float = 0.03):
        self.risk_free_rate = risk_free_rate

    def get_fund_metrics(self, code: str, days: int = 90) -> Optional[Dict]:
        """获取基金的各项指标"""
        hist = get_historical_nav(code, days)
        if len(hist) < 10:
            logger.warning(f"基金 {code} 历史数据不足")
            return None

        quote = get_realtime_quote(code)
        if not quote:
            return None

        # 计算各项指标（使用简单收益率，不年化）
        metrics = {
            'code': code,
            'name': quote.get('name', ''),
            'current_nav': quote.get('estimated_nav', 0) or quote.get('price', 0),
            'update_time': quote.get('update_time', ''),

            # 各周期收益率（简单收益率，不再年化）
            'return_1d': self._calc_simple_return(hist, 1),
            'return_1w': self._calc_simple_return(hist, 7),
            'return_1m': self._calc_simple_return(hist, 30),
            'return_3m': self._calc_simple_return(hist, 90),
            'return_6m': self._calc_simple_return(hist, 180),
            'return_1y': self._calc_simple_return(hist, 365),

            # 历史净值数据
            'hist': hist,

            # 波动率（年化）
            'volatility_1m': self._calc_volatility(hist, 30),
            'volatility_3m': self._calc_volatility(hist, 90),
            'volatility_6m': self._calc_volatility(hist, 180),

            # 夏普比率
            'sharpe_3m': self._calc_sharpe(hist, 90),
            'sharpe_6m': self._calc_sharpe(hist, 180),

            # 最大回撤
            'max_drawdown': self._calc_max_drawdown(hist),

            # 历史高低点
            'high_nav': max(h['nav'] for h in hist),
            'low_nav': min(h['nav'] for h in hist),
        }

        # 计算距离高点的跌幅
        if metrics['high_nav'] > 0:
            metrics['drop_from_high'] = (metrics['current_nav'] - metrics['high_nav']) / metrics['high_nav'] * 100

        return metrics

    def _calc_simple_return(self, hist: List[Dict], days: int) -> float:
        """计算简单收益率（不年化）"""
        if len(hist) < days:
            days = len(hist)
        if days < 2 or len(hist) < 2:
            return 0.0

        start_idx = max(0, len(hist) - days)
        start_nav = hist[start_idx]['nav']
        end_nav = hist[-1]['nav']

        if start_nav <= 0:
            return 0.0

        # 简单收益率，不再年化
        return_pct = (end_nav - start_nav) / start_nav * 100
        return round(return_pct, 2)

    def _calc_volatility(self, hist: List[Dict], days: int) -> float:
        """计算波动率（年化标准差）"""
        if len(hist) < days:
            days = len(hist)
        if days < 10:
            return 0.0

        start_idx = max(0, len(hist) - days)
        prices = [h['nav'] for h in hist[start_idx:]]

        if len(prices) < 2:
            return 0.0

        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)

        if not returns or len(returns) < 2:
            return 0.0

        import statistics
        std_dev = statistics.stdev(returns)
        annual_vol = std_dev * (365 ** 0.5) * 100
        return round(annual_vol, 2)

    def _calc_sharpe(self, hist: List[Dict], days: int) -> float:
        """计算夏普比率"""
        if len(hist) < days:
            days = len(hist)
        if days < 30:
            return 0.0

        start_idx = max(0, len(hist) - days)
        prices = [h['nav'] for h in hist[start_idx:]]

        if len(prices) < 10:
            return 0.0

        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)

        if not returns or len(returns) < 2:
            return 0.0

        import statistics
        mean_return = statistics.mean(returns)
        std_dev = statistics.stdev(returns)

        if std_dev == 0:
            return 0.0

        annual_return = mean_return * 365
        annual_std = std_dev * (365 ** 0.5)

        sharpe = (annual_return - self.risk_free_rate) / annual_std
        return round(sharpe, 2)

    def _calc_max_drawdown(self, hist: List[Dict]) -> float:
        """计算最大回撤"""
        if len(hist) < 2:
            return 0.0

        navs = [h['nav'] for h in hist]
        peak = navs[0]
        max_dd = 0.0

        for nav in navs:
            if nav > peak:
                peak = nav
            dd = (peak - nav) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        return round(max_dd, 2)

    def score_fund(self, metrics: Dict, strategy: str = 'momentum') -> float:
        """根据策略给基金打分"""
        score = 0.0

        if strategy == 'momentum':
            score += metrics.get('return_1m', 0) * 2
            score += metrics.get('return_3m', 0) * 1.5
            score += metrics.get('return_6m', 0) * 1
            vol = metrics.get('volatility_3m', 0)
            if vol > 30:
                score -= 10
            elif vol > 20:
                score -= 5

        elif strategy == 'value':
            drop = metrics.get('drop_from_high', 0)
            if drop < -15:
                score += 15
            elif drop < -10:
                score += 10
            elif drop < -5:
                score += 5

            dd = metrics.get('max_drawdown', 0)
            if dd > 15:
                score += 10
            elif dd > 10:
                score += 5

        elif strategy == 'stable':
            sharpe = metrics.get('sharpe_6m', 0)
            score += sharpe * 20

            dd = metrics.get('max_drawdown', 0)
            if dd > 15:
                score -= 15
            elif dd > 10:
                score -= 5

            score += metrics.get('return_1y', 0) * 0.5

        elif strategy == 'hot':
            score += metrics.get('return_1m', 0) * 3
            score += metrics.get('return_1w', 0) * 2

        return round(score, 2)


def get_fund_analysis(code: str) -> Optional[Dict]:
    """快速获取基金分析结果"""
    analyzer = FundAnalyzer()
    return analyzer.get_fund_metrics(code)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='基金分析工具')
    parser.add_argument('code', help='基金代码')
    parser.add_argument('--days', type=int, default=90, help='分析天数')
    args = parser.parse_args()

    analyzer = FundAnalyzer()
    metrics = analyzer.get_fund_metrics(args.code, args.days)

    if metrics:
        print(f"\n📊 基金分析: {metrics['name']} ({metrics['code']})")
        print(f"   当前净值: {metrics['current_nav']:.4f}")
        print(f"   近1周收益: {metrics['return_1w']:+.2f}%")
        print(f"   近1月收益: {metrics['return_1m']:+.2f}%")
        print(f"   近3月收益: {metrics['return_3m']:+.2f}%")
        print(f"   近6月收益: {metrics['return_6m']:+.2f}%")
        print(f"   波动率(3月): {metrics['volatility_3m']:.2f}%")
        print(f"   夏普比率(6月): {metrics['sharpe_6m']:.2f}")
        print(f"   最大回撤: {metrics['max_drawdown']:.2f}%")
        print(f"   距离高点: {metrics.get('drop_from_high', 0):+.2f}%")
