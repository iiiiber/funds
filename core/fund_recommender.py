#!/usr/bin/env python3
"""基金推荐核心模块 - 多维度筛选优质基金"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.fund_analyzer import FundAnalyzer
from core.news_analyzer import NewsAnalyzer
from core.holdings import HoldingsManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


# 热门基金池（按板块分类）
FUND_POOL = {
    'AI/人工智能': [
        ('015790', '永赢高端装备智选混合C'),
        ('017470', '嘉实上证科创板芯片ETF联接C'),
        ('014855', '嘉实中证半导体产业指数增强C'),
    ],
    '新能源': [
        ('021363', '易方达中证沪深港黄金产业股票指数C'),
    ],
    '消费': [
        ('002611', '博时黄金ETF联接C'),
    ],
    '稳健收益': [
        ('011452', '华泰柏瑞质量成长混合C'),
        ('020065', '西部利得科技创新混合C'),
        ('013403', '华夏恒生科技ETF联接(QDII)C'),
    ],
}


class FundRecommender:
    """基金推荐器"""

    def __init__(self, max_workers: int = 5):
        self.analyzer = FundAnalyzer()
        self.news_analyzer = NewsAnalyzer()
        self.max_workers = max_workers
        self.holdings_mgr = HoldingsManager()

    def analyze_fund(self, code: str, name: str = None) -> Optional[Dict]:
        """分析单个基金"""
        try:
            metrics = self.analyzer.get_fund_metrics(code, days=90)
            if not metrics:
                return None

            if name:
                metrics['name'] = name

            # 计算各策略得分
            metrics['score_momentum'] = self.analyzer.score_fund(metrics, 'momentum')
            metrics['score_value'] = self.analyzer.score_fund(metrics, 'value')
            metrics['score_stable'] = self.analyzer.score_fund(metrics, 'stable')
            metrics['score_hot'] = self.analyzer.score_fund(metrics, 'hot')

            # 综合得分
            metrics['score_total'] = (
                metrics['score_momentum'] * 0.3 +
                metrics['score_value'] * 0.2 +
                metrics['score_stable'] * 0.3 +
                metrics['score_hot'] * 0.2
            )

            return metrics
        except Exception as e:
            logger.error(f"分析基金 {code} 失败: {e}")
            return None

    def get_recommendations(self, strategy: str = None, limit: int = 5) -> List[Dict]:
        """
        获取推荐列表

        Args:
            strategy: 策略类型 (momentum/value/stable/hot/all)
            limit: 返回数量
        """
        # 获取热点板块
        hot_sectors = self.news_analyzer.extract_sectors()
        hot_keywords = [s['keywords'] for s in hot_sectors[:3]]

        logger.info(f"当前热点板块: {[s['sector'] for s in hot_sectors[:3]]}")

        # 构建基金池
        fund_pool = []

        # 1. 持仓基金（已有）
        holdings = self.holdings_mgr.list()
        for h in holdings:
            fund_pool.append((h['code'], h['name']))

        # 2. 热门基金池
        for sector, funds in FUND_POOL.items():
            for code, name in funds:
                if not any(f[0] == code for f in fund_pool):
                    fund_pool.append((code, name))

        logger.info(f"待分析基金数量: {len(fund_pool)}")

        # 并行分析
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.analyze_fund, code, name): (code, name)
                      for code, name in fund_pool}

            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        if not results:
            return []

        # 按策略排序
        if strategy == 'momentum':
            results.sort(key=lambda x: x['score_momentum'], reverse=True)
        elif strategy == 'value':
            results.sort(key=lambda x: x['score_value'], reverse=True)
        elif strategy == 'stable':
            results.sort(key=lambda x: x['score_stable'], reverse=True)
        elif strategy == 'hot':
            results.sort(key=lambda x: x['score_hot'], reverse=True)
        else:
            results.sort(key=lambda x: x['score_total'], reverse=True)

        return results[:limit]

    def generate_reasons(self, fund: Dict, strategy: str, hot_sectors: List[Dict] = None) -> str:
        """
        生成推荐理由

        Args:
            fund: 基金指标
            strategy: 策略类型
            hot_sectors: 热点板块列表
        """
        reasons = []
        name = fund.get('name', '')
        code = fund.get('code', '')

        if strategy == 'momentum':
            # 趋势动量型
            ret_1m = fund.get('return_1m', 0)
            ret_3m = fund.get('return_3m', 0)

            if ret_1m > 5:
                reasons.append(f"近1月涨幅达{ret_1m:.1f}%，趋势强劲")
            elif ret_1m > 0:
                reasons.append(f"近1月上涨{ret_1m:.1f}%，表现稳健")

            if ret_3m > 10:
                reasons.append(f"近3月涨幅{ret_3m:.1f}%，中期趋势向好")

            # 波动率
            vol = fund.get('volatility_3m', 0)
            if vol < 20:
                reasons.append(f"波动率较低({vol:.1f}%)，风险可控")

            # 热点匹配
            if hot_sectors:
                for sector in hot_sectors[:1]:
                    for kw in sector.get('keywords', [])[:2]:
                        if kw in name or any(kw in n for n in [name]):
                            reasons.append(f"涉及{hot_sectors[0]['sector']}热点板块")
                            break

        elif strategy == 'value':
            # 价值低估型
            drop = fund.get('drop_from_high', 0)
            max_dd = fund.get('max_drawdown', 0)

            if drop < -15:
                reasons.append(f"距历史高点回调{abs(drop):.1f}%，逢低布局机会")
            elif drop < -10:
                reasons.append(f"距离高点回调{abs(drop):.1f}%，估值吸引力提升")

            if max_dd > 15:
                reasons.append(f"近期最大回撤{max_dd:.1f}%，风险释放较充分")

        elif strategy == 'stable':
            # 稳健收益型
            sharpe = fund.get('sharpe_6m', 0)
            ret_1y = fund.get('return_1y', 0)
            max_dd = fund.get('max_drawdown', 0)

            if sharpe > 1:
                reasons.append(f"夏普比率{sharpe:.2f}，风险收益比优秀")
            elif sharpe > 0.5:
                reasons.append(f"夏普比率{sharpe:.2f}，收益稳定")

            if ret_1y > 20:
                reasons.append(f"近1年收益{ret_1y:.1f}%，长期表现优异")

            if max_dd < 10:
                reasons.append(f"最大回撤仅{max_dd:.1f}%，抗跌能力强")

        elif strategy == 'hot':
            # 热点轮动型
            ret_1w = fund.get('return_1w', 0)
            ret_1m = fund.get('return_1m', 0)

            if ret_1w > 3:
                reasons.append(f"近1周暴涨{ret_1w:.1f}%，短期爆发力强")
            elif ret_1w > 0:
                reasons.append(f"近1周上涨{ret_1w:.1f}%，热度较高")

            if ret_1m > 5:
                reasons.append(f"近1月涨幅{ret_1m:.1f}%，板块轮动受益")

            if hot_sectors:
                for sector in hot_sectors[:1]:
                    reasons.append(f"受益于{hot_sectors[0]['sector']}热点")

        # 默认理由
        if not reasons:
            reasons.append("综合指标表现良好")

        return "；".join(reasons[:3])

    def get_strategy_recommendations(self, limit: int = 5) -> Dict[str, List[Dict]]:
        """获取各策略推荐"""
        hot_sectors = self.news_analyzer.extract_sectors()

        strategies = ['momentum', 'value', 'stable', 'hot']
        result = {}

        for strategy in strategies:
            funds = self.get_recommendations(strategy, limit)

            for fund in funds:
                fund['reason'] = self.generate_reasons(fund, strategy, hot_sectors)
                fund['strategy'] = strategy

            result[strategy] = funds
            logger.info(f"{strategy} 策略推荐: {len(funds)} 只基金")

        return result

    def save_recommendations(self, filepath: Path = None):
        """保存推荐结果到文件"""
        if filepath is None:
            filepath = Path(__file__).parent.parent / 'data' / 'recommendations.json'

        recommendations = self.get_strategy_recommendations(limit=5)

        # 转换为可序列化格式
        output = {
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'strategies': {}
        }

        strategy_names = {
            'momentum': '趋势动量型',
            'value': '价值低估型',
            'stable': '稳健收益型',
            'hot': '热点轮动型'
        }

        for strategy, funds in recommendations.items():
            output['strategies'][strategy] = {
                'name': strategy_names.get(strategy, strategy),
                'funds': funds
            }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"推荐结果已保存: {filepath}")
        return output


def generate_recommendations():
    """生成推荐（供定时任务调用）"""
    recommender = FundRecommender()
    return recommender.save_recommendations()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='基金推荐工具')
    parser.add_argument('--strategy', choices=['momentum', 'value', 'stable', 'hot', 'all'],
                       default='all', help='推荐策略')
    parser.add_argument('--limit', type=int, default=5, help='推荐数量')
    parser.add_argument('--save', action='store_true', help='保存到文件')
    args = parser.parse_args()

    recommender = FundRecommender()

    if args.strategy == 'all':
        result = recommender.get_strategy_recommendations(args.limit)

        strategy_names = {
            'momentum': '📈 趋势动量型',
            'value': '💎 价值低估型',
            'stable': '🛡️ 稳健收益型',
            'hot': '🔥 热点轮动型'
        }

        for strategy, funds in result.items():
            print(f"\n{'='*50}")
            print(f"{strategy_names.get(strategy, strategy)}")
            print('='*50)

            for i, f in enumerate(funds, 1):
                print(f"\n{i}. {f['name']} ({f['code']})")
                print(f"   综合评分: {f['score_total']:.2f}")
                print(f"   近1月: {f['return_1m']:+.2f}% | 近3月: {f['return_3m']:+.2f}%")
                print(f"   夏普比率: {f['sharpe_6m']:.2f} | 最大回撤: {f['max_drawdown']:.2f}%")
                print(f"   推荐理由: {f.get('reason', '暂无')}")

    else:
        funds = recommender.get_recommendations(args.strategy, args.limit)
        for i, f in enumerate(funds, 1):
            print(f"{i}. {f['name']} ({f['code']}) - {f['score_total']:.2f}")

    if args.save:
        recommender.save_recommendations()
