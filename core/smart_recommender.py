#!/usr/bin/env python3
"""
智能基金推荐器 - 重构版
核心逻辑：
1. 新闻热点分析 → 确定热点板块
2. 板块基金池 → 计算各项指标
3. 综合评分 → 避免追高，顺势而为
"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.fund_analyzer import FundAnalyzer
from core.news_analyzer import NewsAnalyzer
from core.fund_pool import FUND_POOL, SECTOR_KEYWORDS

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


def get_all_funds():
    """获取所有基金"""
    funds = []
    for sector, fund_list in FUND_POOL.items():
        for code, name, tag, note in fund_list:
            funds.append((code, name, sector, note))
    return funds


class SmartRecommender:
    """智能推荐器 - 核心算法"""

    def __init__(self, max_workers: int = 5):
        self.analyzer = FundAnalyzer()
        self.news_analyzer = NewsAnalyzer()
        self.max_workers = max_workers

    def analyze_fund(self, code: str, name: str = None, sector: str = None) -> Optional[Dict]:
        """分析单个基金"""
        try:
            metrics = self.analyzer.get_fund_metrics(code, days=180)
            if not metrics:
                return None

            if name:
                metrics['name'] = name
            if sector:
                metrics['sector'] = sector

            # 计算各项评分
            metrics['scores'] = {
                'momentum': self._score_momentum(metrics),
                'value': self._score_value(metrics),
                'stable': self._score_stable(metrics),
                'hot': self._score_hot(metrics),
            }

            # 综合评分
            metrics['total_score'] = (
                metrics['scores']['momentum'] * 0.3 +
                metrics['scores']['value'] * 0.2 +
                metrics['scores']['stable'] * 0.3 +
                metrics['scores']['hot'] * 0.2
            )

            return metrics
        except Exception as e:
            logger.error(f"分析基金 {code} 失败: {e}")
            return None

    def _score_momentum(self, m: Dict) -> float:
        """
        趋势动量评分
        核心思路：趋势向好但不追高
        - 近期有上涨趋势加分
        - 但如果涨太多（近1月>15%）反而减分（避免追高）
        """
        score = 0.0

        ret_1m = m.get('return_1m', 0)
        ret_3m = m.get('return_3m', 0)
        drop_from_high = m.get('drop_from_high', 0)

        # 近1月涨幅评分（适中加分，过高减分）
        if 0 < ret_1m < 8:
            score += ret_1m * 3  # 温和上涨，好
        elif 8 <= ret_1m <= 15:
            score += 15  # 涨幅适中
        elif ret_1m > 15:
            score -= (ret_1m - 15) * 2  # 涨太多，可能回调
        elif -5 < ret_1m < 0:
            score += ret_1m * 2  # 小幅回调，正常
        else:
            score += ret_1m  # 大幅下跌，负分

        # 近3月涨幅（中期趋势）
        if 5 < ret_3m < 30:
            score += ret_3m * 0.5
        elif ret_3m >= 30:
            score += 10  # 涨幅过大，限制加分

        # 距离高点（合理区间加分）
        if -20 < drop_from_high < -5:
            score += 10  # 回调到合理位置，值得关注
        elif -5 <= drop_from_high <= 0:
            score += 5  # 接近高点，正常

        return round(score, 2)

    def _score_value(self, m: Dict) -> float:
        """
        价值评分
        核心思路：逢低布局，但也要看质地
        """
        score = 0.0

        drop_from_high = m.get('drop_from_high', 0)
        max_dd = m.get('max_drawdown', 0)
        sharpe = m.get('sharpe_6m', 0)

        # 距离高点回调幅度（适度回调加分，过度回调说明基本面可能有问题）
        if -30 < drop_from_high <= -20:
            score += 20  # 回调充分，值得关注
        elif -20 < drop_from_high <= -10:
            score += 15  # 适度回调
        elif -10 < drop_from_high <= -5:
            score += 10  # 小幅回调
        elif drop_from_high > 0:
            score += 5  # 创新高

        # 最大回撤（抗跌性）
        if max_dd < 15:
            score += 15
        elif max_dd < 20:
            score += 10
        elif max_dd < 30:
            score += 5

        # 夏普比率
        if sharpe > 2:
            score += 10
        elif sharpe > 1:
            score += 5

        return round(score, 2)

    def _score_stable(self, m: Dict) -> float:
        """
        稳健评分
        核心思路：长期表现稳定，风险收益比好
        """
        score = 0.0

        sharpe = m.get('sharpe_6m', 0)
        max_dd = m.get('max_drawdown', 0)
        ret_6m = m.get('return_6m', 0)
        volatility = m.get('volatility_3m', 0)

        # 夏普比率（最重要）
        if sharpe > 2:
            score += 30
        elif sharpe > 1.5:
            score += 20
        elif sharpe > 1:
            score += 10

        # 最大回撤
        if max_dd < 10:
            score += 15
        elif max_dd < 15:
            score += 10
        elif max_dd < 20:
            score += 5

        # 波动率（低波动加分）
        if volatility < 15:
            score += 10
        elif volatility < 20:
            score += 5

        # 近6月收益
        if ret_6m > 10:
            score += 10
        elif ret_6m > 0:
            score += 5

        return round(score, 2)

    def _score_hot(self, m: Dict) -> float:
        """
        热点评分
        核心思路：近期表现强劲，受市场关注
        """
        score = 0.0

        ret_1w = m.get('return_1w', 0)
        ret_1m = m.get('return_1m', 0)

        # 近1周涨幅（短期热度）
        if ret_1w > 5:
            score += 20
        elif ret_1w > 3:
            score += 15
        elif ret_1w > 1:
            score += 10
        elif ret_1w > 0:
            score += 5

        # 近1月涨幅
        if 5 < ret_1m < 12:
            score += 15  # 温和上涨
        elif 0 < ret_1m <= 5:
            score += 10

        return round(score, 2)

    def get_hot_sectors_with_funds(self) -> Dict:
        """获取热点板块及其基金"""
        sectors = self.news_analyzer.extract_sectors()

        result = {
            'sectors': [],
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        for sector_data in sectors[:5]:
            sector_name = sector_data['sector']

            # 找对应的基金
            matched_funds = FUND_POOL.get(sector_name, [])

            if matched_funds:
                sector_data['funds'] = matched_funds
                sector_data['match_type'] = 'direct'
            else:
                # 模糊匹配
                keywords = SECTOR_KEYWORDS.get(sector_name, [])
                matched = self._fuzzy_match_sector(sector_name, keywords)
                sector_data['funds'] = matched
                sector_data['match_type'] = 'fuzzy'

            result['sectors'].append(sector_data)

        return result

    def _fuzzy_match_sector(self, sector_name: str, keywords: List[str]) -> List[Tuple]:
        """模糊匹配板块基金"""
        matched = []

        for s, funds in FUND_POOL.items():
            # 检查关键词重叠
            kw2 = SECTOR_KEYWORDS.get(s, [])
            overlap = set(keywords) & set(kw2)

            if overlap or any(k in s for k in keywords):
                matched.extend(funds[:5])  # 最多取5只

        return matched[:10]

    def generate_recommendations(self, top_n: int = 5) -> Dict:
        """生成推荐结果"""
        logger.info("开始生成智能推荐...")

        # 获取热点板块
        hot_sectors = self.news_analyzer.extract_sectors()
        logger.info(f"热点板块: {[s['sector'] for s in hot_sectors[:5]]}")

        # 获取所有基金
        all_funds = get_all_funds()
        logger.info(f"基金候选池: {len(all_funds)} 只")

        # 并行分析所有基金
        analyzed = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.analyze_fund, code, name, sector): (code, name, sector)
                for code, name, sector, _ in all_funds
            }

            for future in as_completed(futures):
                result = future.result()
                if result:
                    analyzed.append(result)

        logger.info(f"成功分析: {len(analyzed)} 只基金")

        if not analyzed:
            return {'strategies': {}, 'hot_sectors': [], 'update_time': ''}

        # 按策略分组
        strategies = {
            'momentum': {'name': '📈 趋势动量型', 'funds': []},
            'value': {'name': '💎 价值低估型', 'funds': []},
            'stable': {'name': '🛡️ 稳健收益型', 'funds': []},
            'hot': {'name': '🔥 热点轮动型', 'funds': []},
        }

        # 分配到各策略
        for fund in analyzed:
            scores = fund.get('scores', {})

            for strategy in ['momentum', 'value', 'stable', 'hot']:
                fund_copy = {**fund}
                fund_copy['score'] = scores.get(strategy, 0)
                fund_copy['strategy'] = strategy
                fund_copy['reason'] = self._generate_reason(fund_copy, strategy, hot_sectors)
                strategies[strategy]['funds'].append(fund_copy)

        # 排序并截取
        for strategy in strategies:
            strategies[strategy]['funds'].sort(key=lambda x: x['score'], reverse=True)
            strategies[strategy]['funds'] = strategies[strategy]['funds'][:top_n]

        # 构建结果
        result = {
            'strategies': strategies,
            'hot_sectors': hot_sectors[:5],
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        return result

    def _generate_reason(self, fund: Dict, strategy: str, hot_sectors: List) -> str:
        """生成推荐理由"""
        reasons = []
        name = fund.get('name', '')
        sector = fund.get('sector', '')

        ret_1m = fund.get('return_1m', 0)
        ret_3m = fund.get('return_3m', 0)
        sharpe = fund.get('sharpe_6m', 0)
        max_dd = fund.get('max_drawdown', 0)
        drop = fund.get('drop_from_high', 0)

        if strategy == 'momentum':
            if 3 < ret_1m < 12:
                reasons.append(f"近1月温和上涨{ret_1m:.1f}%，趋势向好")
            elif ret_3m > 10:
                reasons.append(f"近3月涨幅{ret_3m:.1f}%，中期表现强劲")
            if sharpe > 1.5:
                reasons.append(f"夏普比率{sharpe:.2f}，收益稳定")
            if -15 < drop < -3:
                reasons.append(f"距高点回调{abs(drop):.1f}%，介入点位适中")

        elif strategy == 'value':
            if -25 < drop <= -15:
                reasons.append(f"回调充分（距高点{abs(drop):.1f}%），估值吸引力提升")
            elif -15 < drop <= -5:
                reasons.append(f"适度回调{abs(drop):.1f}%，性价比较高")
            if max_dd < 15:
                reasons.append(f"最大回撤控制良好（{max_dd:.1f}%）")
            if sharpe > 1:
                reasons.append(f"夏普比率{sharpe:.2f}，风险收益比不错")

        elif strategy == 'stable':
            if sharpe > 1.5:
                reasons.append(f"夏普比率{sharpe:.2f}，长期收益稳定")
            if max_dd < 10:
                reasons.append(f"最大回撤仅{max_dd:.1f}%，抗跌能力强")
            if ret_3m > 5:
                reasons.append(f"近3月上涨{ret_3m:.1f}%，表现稳健")
            reasons.append("适合长期持有")

        elif strategy == 'hot':
            # 检查是否匹配热点
            for hs in hot_sectors[:2]:
                sector_kw = hs.get('keywords', [])
                if any(kw in name or kw in sector for kw in sector_kw):
                    reasons.append(f"受益于{hs['sector']}热点")
                    break

            if fund.get('return_1w', 0) > 2:
                reasons.append(f"近1周上涨{fund['return_1w']:.1f}%，市场关注度高")
            if 5 < ret_1m < 12:
                reasons.append(f"近期表现活跃，上涨趋势明确")

        if not reasons:
            reasons.append("综合指标表现良好，可关注")

        return "；".join(reasons[:3])

    def save_recommendations(self, filepath: Path = None):
        """保存推荐结果"""
        if filepath is None:
            filepath = Path(__file__).parent.parent / 'data' / 'recommendations.json'

        result = self.generate_recommendations(top_n=5)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"推荐结果已保存: {filepath}")
        return result


def main():
    """测试运行"""
    recommender = SmartRecommender()
    result = recommender.generate_recommendations(top_n=5)

    print(f"\n更新时间: {result['update_time']}")
    print("\n" + "="*60)
    print("🔥 热点板块")
    print("="*60)
    for s in result.get('hot_sectors', [])[:5]:
        print(f"  {s['sector']} (热度:{s['score']}) | 关键词:{','.join(s['keywords'][:3])}")

    for strategy, data in result.get('strategies', {}).items():
        print("\n" + "="*60)
        print(data['name'])
        print("="*60)

        for i, f in enumerate(data['funds'], 1):
            print(f"\n{i}. {f['name']} ({f['code']})")
            print(f"   板块: {f.get('sector', '未知')}")
            print(f"   近1月: {f['return_1m']:+.2f}% | 近3月: {f['return_3m']:+.2f}%")
            print(f"   夏普比率: {f['sharpe_6m']:.2f} | 最大回撤: {f['max_drawdown']:.2f}%")
            print(f"   综合评分: {f['score']:.2f}")
            print(f"   推荐理由: {f['reason']}")


if __name__ == '__main__':
    main()
