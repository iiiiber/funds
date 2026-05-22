"""智能基金推荐系统"""
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RecommendType(Enum):
    """推荐类型"""
    MOMENTUM = "momentum"           # 动量型：追涨强势基金
    CONTRARIAN = "contrarian"       # 反转型：超跌反弹机会
    LOW_VOLATILITY = "low_vol"      # 稳健型：低波动高夏普
    DIVERSIFICATION = "diversify"   # 分散型：互补现有持仓
    HIGH_SHARPE = "high_sharpe"     # 高夏普：高风险调整收益


@dataclass
class FundMetrics:
    """基金指标数据"""
    code: str
    name: str
    nav_list: List[Dict]
    
    # 基础指标
    volatility: float = 0.0         # 年化波动率
    sharpe_ratio: float = 0.0       # 夏普比率
    max_drawdown: float = 0.0       # 最大回撤
    
    # 动量指标
    momentum_20d: float = 0.0       # 20日动量
    momentum_60d: float = 0.0       # 60日动量
    momentum_90d: float = 0.0       # 90日动量
    
    # 综合评分
    composite_score: float = 0.0    # 综合评分
    risk_score: float = 0.0         # 风险评分


# ========== 同类基金去重映射 ==========
# 同一指数的 ETF 和联接基金，只保留一只（优先保留 ETF）
INDEX_DEDUP_MAP = {
    # 沪深300
    "510300": "510300", "159919": "510300", "000961": "510300", 
    "110020": "510300", "001143": "510300",
    # 中证500
    "510500": "510500", "000962": "510500",
    # 创业板
    "159915": "159915", "110026": "159915", "001592": "159915",
    # 科创50
    "588000": "588000", "588050": "588000", "588080": "588000",
    # 上证50
    "510050": "510050", "510100": "510050",
}

# 波动率阈值：低于此值的基金视为"纯债/货币类"，动量型策略排除
MIN_VOLATILITY_FOR_MOMENTUM = 0.10  # 10%波动率


def get_dedup_key(code: str) -> str:
    """获取去重后的唯一键"""
    return INDEX_DEDUP_MAP.get(code, code)


class SmartRecommender:
    """智能推荐引擎"""
    
    def __init__(self, db=None, fund_api=None):
        self.db = db
        self.fund_api = fund_api
    
    def calculate_metrics(self, code: str, name: str, nav_list: List[Dict]) -> FundMetrics:
        """计算基金各项指标"""
        metrics = FundMetrics(code=code, name=name, nav_list=nav_list)
        
        if len(nav_list) < 20:
            return metrics
        
        # 计算日收益率
        returns = []
        nav_values = []
        dates = []
        
        for i, nav_data in enumerate(nav_list):
            nav = float(nav_data.get('nav', 0))
            nav_values.append(nav)
            dates.append(nav_data.get('date', ''))
            
            if i > 0 and nav > 0:
                prev_nav = float(nav_list[i-1].get('nav', 0))
                if prev_nav > 0:
                    ret = (nav - prev_nav) / prev_nav
                    returns.append(ret)
        
        # 1. 计算波动率 (年化)
        if len(returns) >= 2:
            mean_ret = sum(returns) / len(returns)
            variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
            std = math.sqrt(variance)
            metrics.volatility = std * math.sqrt(252)
        
        # 2. 计算最大回撤
        if nav_values:
            peak = nav_values[0]
            max_dd = 0.0
            for nav in nav_values:
                if nav > peak:
                    peak = nav
                dd = (peak - nav) / peak if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
            metrics.max_drawdown = max_dd
        
        # 3. 计算夏普比率
        if metrics.volatility > 0 and len(nav_values) >= 2:
            first_nav = nav_values[0]
            last_nav = nav_values[-1]
            days = len(nav_values) - 1
            total_return = (last_nav - first_nav) / first_nav
            annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
            risk_free = 0.03  # 3% 无风险利率
            metrics.sharpe_ratio = (annual_return - risk_free) / metrics.volatility
        
        # 4. 计算动量指标
        latest_nav = nav_values[-1] if nav_values else 0
        
        for period, attr in [(20, 'momentum_20d'), (60, 'momentum_60d'), (90, 'momentum_90d')]:
            if len(nav_values) >= period:
                past_nav = nav_values[-period]
                if past_nav > 0:
                    momentum = (latest_nav - past_nav) / past_nav * 100
                    setattr(metrics, attr, momentum)
        
        # 5. 风险评分 (0-100)
        metrics.risk_score = max(0, min(100, int((metrics.volatility - 0.10) / 0.40 * 100)))
        
        return metrics
    
    def calculate_composite_score(self, metrics: FundMetrics, 
                                   recommend_type: RecommendType) -> float:
        """根据推荐类型计算综合评分 - 修复版"""
        
        # 标准化函数 (Min-Max归一化到0-1)
        def normalize(value: float, min_val: float, max_val: float) -> float:
            if max_val == min_val:
                return 0.5
            return max(0, min(1, (value - min_val) / (max_val - min_val)))
        
        # 获取指标值
        momentum = metrics.momentum_90d
        recent_mom = metrics.momentum_20d
        volatility = metrics.volatility
        sharpe = metrics.sharpe_ratio
        max_dd = metrics.max_drawdown
        
        # ========== 各推荐类型的权重 (修复版) ==========
        
        if recommend_type == RecommendType.MOMENTUM:
            # 动量型：追涨强势基金
            # 问题：债券低波动得高分 → 修复：惩罚低波动 + 近期动量权重
            
            # 波动率惩罚：低于15%波动的基金降权（排除纯债）
            vol_penalty = 1.0 if volatility >= 0.15 else volatility / 0.15 * 0.3
            
            # 近期动量（20日）权重最高
            recent_strength = normalize(recent_mom, -10, 25) * 0.4
            # 中期动量（90日）
            mid_term = normalize(momentum, -15, 35) * 0.3
            # 夏普比率辅助
            sharpe_score = normalize(sharpe, 0, 3) * 0.2
            # 回撤控制
            dd_score = normalize(-max_dd, -0.25, 0) * 0.1
            
            score = (recent_strength + mid_term + sharpe_score + dd_score) * vol_penalty
            
        elif recommend_type == RecommendType.CONTRARIAN:
            # 反转型：超跌反弹机会
            # 问题：追涨基金得分高 → 修复：优先近期下跌 + 中长期稳健
            
            # 近期跌幅越大得分越高（但不能太极端）
            recent_decline = normalize(-recent_mom, -20, 15) * 0.35
            # 中长期表现不能太差（需要已经企稳）
            mid_term_stability = normalize(momentum, -5, 25) * 0.3
            # 波动率适中（不能太大）
            vol_control = normalize(-volatility, 0.10, 0.35) * 0.2
            # 夏普辅助
            sharpe_score = normalize(sharpe, -0.5, 2.5) * 0.15
            
            score = recent_decline + mid_term_stability + vol_control + sharpe_score
            
        elif recommend_type == RecommendType.LOW_VOLATILITY:
            # 稳健型：低波动高夏普
            # 波动率权重最高
            vol_score = normalize(-volatility, 0.02, 0.30) * 0.45
            # 夏普比率
            sharpe_score = normalize(sharpe, 0, 3) * 0.3
            # 回撤控制
            dd_score = normalize(-max_dd, -0.15, 0) * 0.25
            
            score = vol_score + sharpe_score + dd_score
            
        elif recommend_type == RecommendType.HIGH_SHARPE:
            # 高夏普：风险调整收益最优
            # 夏普比率权重最高
            sharpe_score = normalize(sharpe, 0.5, 4) * 0.5
            # 近期动量
            recent_strength = normalize(recent_mom, -10, 25) * 0.2
            # 回撤控制
            dd_score = normalize(-max_dd, -0.25, 0) * 0.2
            # 波动率适中
            vol_control = normalize(-volatility, 0.08, 0.35) * 0.1
            
            score = sharpe_score + recent_strength + dd_score + vol_control
            
        elif recommend_type == RecommendType.DIVERSIFICATION:
            # 分散型：综合考虑，补充现有持仓
            # 动量适中（不能太极端）
            momentum_balanced = normalize(abs(momentum), 0, 30) * 0.25
            # 夏普中等偏上
            sharpe_score = normalize(sharpe, 0, 2.5) * 0.3
            # 波动率中等（与现有持仓形成互补）
            vol_median = normalize(-abs(volatility - 0.20), -0.15, 0.15) * 0.25
            # 回撤可控
            dd_score = normalize(-max_dd, -0.20, 0) * 0.2
            
            score = momentum_balanced + sharpe_score + vol_median + dd_score
        
        metrics.composite_score = score * 100  # 转为0-100分
        return metrics.composite_score
    
    def recommend(self, 
                  fund_pool: List[str],
                  fund_names: Dict[str, str],
                  exclude_codes: List[str] = None,
                  recommend_type: RecommendType = RecommendType.MOMENTUM,
                  limit: int = 6,
                  get_nav_func=None,
                  deduplicate: bool = True) -> List[Dict]:
        """
        推荐基金
        
        Args:
            fund_pool: 候选基金代码列表
            fund_names: 基金代码到名称的映射
            exclude_codes: 排除的基金代码（已持仓等）
            recommend_type: 推荐类型
            limit: 返回数量
            get_nav_func: 获取净值数据的函数
            deduplicate: 是否去重（同一指数只保留一只）
        """
        if exclude_codes is None:
            exclude_codes = []
        
        results = []
        seen_dedup_keys = set()  # 用于去重
        
        for code in fund_pool:
            # 排除已持仓
            if code in exclude_codes:
                continue
            
            # 获取历史净值
            nav_list = get_nav_func(code, days=90) if get_nav_func else []
            
            if len(nav_list) < 20:
                continue
            
            # 计算指标
            name = fund_names.get(code, code)
            metrics = self.calculate_metrics(code, name, nav_list)
            
            # ========== 修复：波动率过滤 ==========
            # 动量型策略排除低波动基金（债券/货币类）
            if recommend_type == RecommendType.MOMENTUM:
                if metrics.volatility < MIN_VOLATILITY_FOR_MOMENTUM:
                    continue  # 跳过低波动基金
            
            # ========== 修复：同类基金去重 ==========
            if deduplicate:
                dedup_key = get_dedup_key(code)
                if dedup_key in seen_dedup_keys:
                    continue  # 已见过同类基金，跳过
                seen_dedup_keys.add(dedup_key)
            
            # 计算综合评分
            score = self.calculate_composite_score(metrics, recommend_type)
            
            results.append({
                'code': code,
                'name': name,
                'score': round(score, 1),
                'momentum_20d': round(metrics.momentum_20d, 2),
                'momentum_60d': round(metrics.momentum_60d, 2),
                'momentum_90d': round(metrics.momentum_90d, 2),
                'volatility': round(metrics.volatility * 100, 2),
                'sharpe_ratio': round(metrics.sharpe_ratio, 2),
                'max_drawdown': round(metrics.max_drawdown * 100, 2),
                'risk_score': round(metrics.risk_score, 1),
                'recommend_type': recommend_type.value,
                'analysis_date': nav_list[-1].get('date', '') if nav_list else '',
            })
        
        # 按评分排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:limit]
    
    def find_similar_funds(self, 
                          target_code: str,
                          fund_pool: List[str],
                          fund_names: Dict[str, str],
                          exclude_codes: List[str] = None,
                          limit: int = 5,
                          get_nav_func=None) -> List[Dict]:
        """
        查找与目标基金相似的基金
        
        基于：
        1. 收益率相关性
        2. 波动率相似度
        3. 风险收益特征相似度
        """
        if exclude_codes is None:
            exclude_codes = []
        
        # 获取目标基金数据
        target_nav = get_nav_func(target_code, days=180) if get_nav_func else []
        if len(target_nav) < 30:
            return []
        
        target_metrics = self.calculate_metrics(
            target_code, 
            fund_names.get(target_code, target_code), 
            target_nav
        )
        
        # 计算目标基金的日收益率序列
        target_returns = []
        for i in range(1, len(target_nav)):
            prev_nav = float(target_nav[i-1].get('nav', 0))
            curr_nav = float(target_nav[i].get('nav', 0))
            if prev_nav > 0:
                target_returns.append((curr_nav - prev_nav) / prev_nav)
        
        similar_funds = []
        
        for code in fund_pool:
            if code == target_code or code in exclude_codes:
                continue
            
            nav_list = get_nav_func(code, days=180) if get_nav_func else []
            if len(nav_list) < 30:
                continue
            
            metrics = self.calculate_metrics(code, fund_names.get(code, code), nav_list)
            
            # 计算日收益率序列
            fund_returns = []
            for i in range(1, len(nav_list)):
                prev_nav = float(nav_list[i-1].get('nav', 0))
                curr_nav = float(nav_list[i].get('nav', 0))
                if prev_nav > 0:
                    fund_returns.append((curr_nav - prev_nav) / prev_nav)
            
            # 计算相关性 (使用对齐的收益率序列)
            min_len = min(len(target_returns), len(fund_returns))
            if min_len < 20:
                continue
                
            # 取最近的数据对齐
            t_ret = target_returns[-min_len:]
            f_ret = fund_returns[-min_len:]
            
            # Pearson相关系数
            t_mean = sum(t_ret) / len(t_ret)
            f_mean = sum(f_ret) / len(f_ret)
            
            numerator = sum((t - t_mean) * (f - f_mean) for t, f in zip(t_ret, f_ret))
            t_var = sum((t - t_mean) ** 2 for t in t_ret)
            f_var = sum((f - f_mean) ** 2 for f in f_ret)
            
            denom = math.sqrt(t_var * f_var)
            correlation = numerator / denom if denom > 0 else 0
            
            # 相似度 = 相关性权重 + 波动率相似度 + 收益特征相似度
            vol_similarity = 1 - abs(target_metrics.volatility - metrics.volatility)
            sharpe_similarity = 1 - abs(target_metrics.sharpe_ratio - metrics.sharpe_ratio) / 2
            
            # 综合相似度 (相关性太高反而不好，要有一定分散)
            similarity = (abs(correlation) * 0.4 + 
                         vol_similarity * 0.3 + 
                         sharpe_similarity * 0.3)
            
            similar_funds.append({
                'code': code,
                'name': fund_names.get(code, code),
                'similarity': round(similarity * 100, 1),
                'correlation': round(correlation, 3),
                'momentum_90d': round(metrics.momentum_90d, 2),
                'volatility': round(metrics.volatility * 100, 2),
                'sharpe_ratio': round(metrics.sharpe_ratio, 2),
            })
        
        # 按相似度排序
        similar_funds.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similar_funds[:limit]
    
    def get_portfolio_analysis(self, holdings: list, get_nav_func) -> dict:
        """分析持仓组合特征（增强版）"""
        if not holdings:
            return {
                'avg_volatility': 0,
                'avg_sharpe': 0,
                'avg_momentum': 0,
                'diversification_score': 0,
                'risk_level': '未持仓',
                'recommendations': [],
                'portfolio_score': 0,
                'holdings_count': 0,
            }

        all_metrics = []
        nav_lists_map = {}
        for h in holdings:
            nav_list = get_nav_func(h['code'], days=90)
            if len(nav_list) >= 20:
                m = self.calculate_metrics(h['code'], h.get('name', h['code']), nav_list)
                all_metrics.append(m)
                nav_lists_map[h['code']] = nav_list

        if not all_metrics:
            return {
                'avg_volatility': 0,
                'avg_sharpe': 0,
                'avg_momentum': 0,
                'diversification_score': 0,
                'risk_level': '数据不足',
                'recommendations': [],
                'portfolio_score': 0,
                'holdings_count': 0,
            }

        avg_vol = sum(m.volatility for m in all_metrics) / len(all_metrics)
        avg_sharpe = sum(m.sharpe_ratio for m in all_metrics) / len(all_metrics)
        avg_mom = sum(m.momentum_90d for m in all_metrics) / len(all_metrics)

        if avg_vol < 0.15:
            risk_level = "保守型"
        elif avg_vol < 0.25:
            risk_level = "稳健型"
        elif avg_vol < 0.35:
            risk_level = "积极型"
        else:
            risk_level = "激进型"

        codes = list(nav_lists_map.keys())
        if len(codes) >= 2:
            import math
            correlations = []
            for i in range(len(codes)):
                for j in range(i + 1, len(codes)):
                    corr = self._calc_correlation(nav_lists_map[codes[i]], nav_lists_map[codes[j]])
                    if corr is not None:
                        correlations.append(corr)
            if correlations:
                avg_corr = sum(correlations) / len(correlations)
                diversification_score = max(0, min(100, int((1 - avg_corr) * 100)))
            else:
                diversification_score = 50
        else:
            diversification_score = 60

        sharpe_score = min(30, avg_sharpe * 10)
        vol_score = max(0, 25 - (avg_vol * 100 - 10) * 0.5)
        div_score = diversification_score * 0.2
        mom_score = max(-5, min(10, avg_mom * 0.5))
        count_score = min(10, len(all_metrics) * 2)
        portfolio_score = round(sharpe_score + vol_score + div_score + mom_score + count_score, 1)
        portfolio_score = max(0, min(100, portfolio_score))

        sorted_by_sharpe = sorted(all_metrics, key=lambda x: x.sharpe_ratio, reverse=True)
        best_fund = {'code': sorted_by_sharpe[0].code, 'name': sorted_by_sharpe[0].name, 'sharpe': round(sorted_by_sharpe[0].sharpe_ratio, 2)} if sorted_by_sharpe else None
        worst_fund = {'code': sorted_by_sharpe[-1].code, 'name': sorted_by_sharpe[-1].name, 'sharpe': round(sorted_by_sharpe[-1].sharpe_ratio, 2)} if sorted_by_sharpe else None

        returns_1m = []
        for m in all_metrics:
            r = (m.momentum_20d / 20) * 22 if m.momentum_20d else 0
            returns_1m.append(r)
        avg_return_1m = sum(returns_1m) / len(returns_1m) if returns_1m else 0

        return {
            'avg_volatility': round(avg_vol * 100, 2),
            'avg_sharpe': round(avg_sharpe, 2),
            'avg_momentum': round(avg_mom, 2),
            'diversification_score': diversification_score,
            'risk_level': risk_level,
            'holdings_count': len(all_metrics),
            'portfolio_score': portfolio_score,
            'avg_return_1m': round(avg_return_1m, 2),
            'best_fund': best_fund,
            'worst_fund': worst_fund,
            'correlation_avg': round(sum(correlations) / len(correlations), 3) if correlations else 0,
            'recommendations': [],
        }

    def _calc_correlation(self, nav_list1: list, nav_list2: list):
        """计算两个净值序列的相关系数"""
        import math
        if len(nav_list1) < 10 or len(nav_list2) < 10:
            return None
        n = min(len(nav_list1), len(nav_list2))
        nav1, nav2 = nav_list1[-n:], nav_list2[-n:]
        prices1 = [h['nav'] for h in nav1]
        prices2 = [h['nav'] for h in nav2]
        returns1 = [(prices1[i] - prices1[i-1]) / prices1[i-1] for i in range(1, n)]
        returns2 = [(prices2[i] - prices2[i-1]) / prices2[i-1] for i in range(1, n)]
        if len(returns1) < 10:
            return None
        mean1 = sum(returns1) / len(returns1)
        mean2 = sum(returns2) / len(returns2)
        cov = sum((returns1[i] - mean1) * (returns2[i] - mean2) for i in range(len(returns1))) / len(returns1)
        std1 = math.sqrt(sum((r - mean1) ** 2 for r in returns1) / len(returns1))
        std2 = math.sqrt(sum((r - mean2) ** 2 for r in returns2) / len(returns2))
        if std1 == 0 or std2 == 0:
            return None
        return cov / (std1 * std2)

"""智能基金推荐系统"""
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RecommendType(Enum):
    """推荐类型"""
    MOMENTUM = "momentum"           # 动量型：追涨强势基金
    CONTRARIAN = "contrarian"       # 反转型：超跌反弹机会
    LOW_VOLATILITY = "low_vol"      # 稳健型：低波动高夏普
    DIVERSIFICATION = "diversify"   # 分散型：互补现有持仓
    HIGH_SHARPE = "high_sharpe"     # 高夏普：高风险调整收益


@dataclass
class FundMetrics:
    """基金指标数据"""
    code: str
    name: str
    nav_list: List[Dict]
    
    # 基础指标
    volatility: float = 0.0         # 年化波动率
    sharpe_ratio: float = 0.0       # 夏普比率
    max_drawdown: float = 0.0       # 最大回撤
    
    # 动量指标
    momentum_20d: float = 0.0       # 20日动量
    momentum_60d: float = 0.0       # 60日动量
    momentum_90d: float = 0.0       # 90日动量
    
    # 综合评分
    composite_score: float = 0.0    # 综合评分
    risk_score: float = 0.0         # 风险评分


# ========== 同类基金去重映射 ==========
# 同一指数的 ETF 和联接基金，只保留一只（优先保留 ETF）
INDEX_DEDUP_MAP = {
    # 沪深300
    "510300": "510300", "159919": "510300", "000961": "510300", 
    "110020": "510300", "001143": "510300",
    # 中证500
    "510500": "510500", "000962": "510500",
    # 创业板
    "159915": "159915", "110026": "159915", "001592": "159915",
    # 科创50
    "588000": "588000", "588050": "588000", "588080": "588000",
    # 上证50
    "510050": "510050", "510100": "510050",
}

# 波动率阈值：低于此值的基金视为"纯债/货币类"，动量型策略排除
MIN_VOLATILITY_FOR_MOMENTUM = 0.10  # 10%波动率


def get_dedup_key(code: str) -> str:
    """获取去重后的唯一键"""
    return INDEX_DEDUP_MAP.get(code, code)


class SmartRecommender:
    """智能推荐引擎"""
    
    def __init__(self, db=None, fund_api=None):
        self.db = db
        self.fund_api = fund_api
    
    def calculate_metrics(self, code: str, name: str, nav_list: List[Dict]) -> FundMetrics:
        """计算基金各项指标"""
        metrics = FundMetrics(code=code, name=name, nav_list=nav_list)
        
        if len(nav_list) < 20:
            return metrics
        
        # 计算日收益率
        returns = []
        nav_values = []
        dates = []
        
        for i, nav_data in enumerate(nav_list):
            nav = float(nav_data.get('nav', 0))
            nav_values.append(nav)
            dates.append(nav_data.get('date', ''))
            
            if i > 0 and nav > 0:
                prev_nav = float(nav_list[i-1].get('nav', 0))
                if prev_nav > 0:
                    ret = (nav - prev_nav) / prev_nav
                    returns.append(ret)
        
        # 1. 计算波动率 (年化)
        if len(returns) >= 2:
            mean_ret = sum(returns) / len(returns)
            variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
            std = math.sqrt(variance)
            metrics.volatility = std * math.sqrt(252)
        
        # 2. 计算最大回撤
        if nav_values:
            peak = nav_values[0]
            max_dd = 0.0
            for nav in nav_values:
                if nav > peak:
                    peak = nav
                dd = (peak - nav) / peak if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
            metrics.max_drawdown = max_dd
        
        # 3. 计算夏普比率
        if metrics.volatility > 0 and len(nav_values) >= 2:
            first_nav = nav_values[0]
            last_nav = nav_values[-1]
            days = len(nav_values) - 1
            total_return = (last_nav - first_nav) / first_nav
            annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0
            risk_free = 0.03  # 3% 无风险利率
            metrics.sharpe_ratio = (annual_return - risk_free) / metrics.volatility
        
        # 4. 计算动量指标
        latest_nav = nav_values[-1] if nav_values else 0
        
        for period, attr in [(20, 'momentum_20d'), (60, 'momentum_60d'), (90, 'momentum_90d')]:
            if len(nav_values) >= period:
                past_nav = nav_values[-period]
                if past_nav > 0:
                    momentum = (latest_nav - past_nav) / past_nav * 100
                    setattr(metrics, attr, momentum)
        
        # 5. 风险评分 (0-100)
        metrics.risk_score = max(0, min(100, int((metrics.volatility - 0.10) / 0.40 * 100)))
        
        return metrics
    
    def calculate_composite_score(self, metrics: FundMetrics, 
                                   recommend_type: RecommendType) -> float:
        """根据推荐类型计算综合评分 - 修复版"""
        
        # 标准化函数 (Min-Max归一化到0-1)
        def normalize(value: float, min_val: float, max_val: float) -> float:
            if max_val == min_val:
                return 0.5
            return max(0, min(1, (value - min_val) / (max_val - min_val)))
        
        # 获取指标值
        momentum = metrics.momentum_90d
        recent_mom = metrics.momentum_20d
        volatility = metrics.volatility
        sharpe = metrics.sharpe_ratio
        max_dd = metrics.max_drawdown
        
        # ========== 各推荐类型的权重 (修复版) ==========
        
        if recommend_type == RecommendType.MOMENTUM:
            # 动量型：追涨强势基金
            # 问题：债券低波动得高分 → 修复：惩罚低波动 + 近期动量权重
            
            # 波动率惩罚：低于15%波动的基金降权（排除纯债）
            vol_penalty = 1.0 if volatility >= 0.15 else volatility / 0.15 * 0.3
            
            # 近期动量（20日）权重最高
            recent_strength = normalize(recent_mom, -10, 25) * 0.4
            # 中期动量（90日）
            mid_term = normalize(momentum, -15, 35) * 0.3
            # 夏普比率辅助
            sharpe_score = normalize(sharpe, 0, 3) * 0.2
            # 回撤控制
            dd_score = normalize(-max_dd, -0.25, 0) * 0.1
            
            score = (recent_strength + mid_term + sharpe_score + dd_score) * vol_penalty
            
        elif recommend_type == RecommendType.CONTRARIAN:
            # 反转型：超跌反弹机会
            # 问题：追涨基金得分高 → 修复：优先近期下跌 + 中长期稳健
            
            # 近期跌幅越大得分越高（但不能太极端）
            recent_decline = normalize(-recent_mom, -20, 15) * 0.35
            # 中长期表现不能太差（需要已经企稳）
            mid_term_stability = normalize(momentum, -5, 25) * 0.3
            # 波动率适中（不能太大）
            vol_control = normalize(-volatility, 0.10, 0.35) * 0.2
            # 夏普辅助
            sharpe_score = normalize(sharpe, -0.5, 2.5) * 0.15
            
            score = recent_decline + mid_term_stability + vol_control + sharpe_score
            
        elif recommend_type == RecommendType.LOW_VOLATILITY:
            # 稳健型：低波动高夏普
            # 波动率权重最高
            vol_score = normalize(-volatility, 0.02, 0.30) * 0.45
            # 夏普比率
            sharpe_score = normalize(sharpe, 0, 3) * 0.3
            # 回撤控制
            dd_score = normalize(-max_dd, -0.15, 0) * 0.25
            
            score = vol_score + sharpe_score + dd_score
            
        elif recommend_type == RecommendType.HIGH_SHARPE:
            # 高夏普：风险调整收益最优
            # 夏普比率权重最高
            sharpe_score = normalize(sharpe, 0.5, 4) * 0.5
            # 近期动量
            recent_strength = normalize(recent_mom, -10, 25) * 0.2
            # 回撤控制
            dd_score = normalize(-max_dd, -0.25, 0) * 0.2
            # 波动率适中
            vol_control = normalize(-volatility, 0.08, 0.35) * 0.1
            
            score = sharpe_score + recent_strength + dd_score + vol_control
            
        elif recommend_type == RecommendType.DIVERSIFICATION:
            # 分散型：综合考虑，补充现有持仓
            # 动量适中（不能太极端）
            momentum_balanced = normalize(abs(momentum), 0, 30) * 0.25
            # 夏普中等偏上
            sharpe_score = normalize(sharpe, 0, 2.5) * 0.3
            # 波动率中等（与现有持仓形成互补）
            vol_median = normalize(-abs(volatility - 0.20), -0.15, 0.15) * 0.25
            # 回撤可控
            dd_score = normalize(-max_dd, -0.20, 0) * 0.2
            
            score = momentum_balanced + sharpe_score + vol_median + dd_score
        
        metrics.composite_score = score * 100  # 转为0-100分
        return metrics.composite_score
    
    def recommend(self, 
                  fund_pool: List[str],
                  fund_names: Dict[str, str],
                  exclude_codes: List[str] = None,
                  recommend_type: RecommendType = RecommendType.MOMENTUM,
                  limit: int = 6,
                  get_nav_func=None,
                  deduplicate: bool = True) -> List[Dict]:
        """
        推荐基金
        
        Args:
            fund_pool: 候选基金代码列表
            fund_names: 基金代码到名称的映射
            exclude_codes: 排除的基金代码（已持仓等）
            recommend_type: 推荐类型
            limit: 返回数量
            get_nav_func: 获取净值数据的函数
            deduplicate: 是否去重（同一指数只保留一只）
        """
        if exclude_codes is None:
            exclude_codes = []
        
        results = []
        seen_dedup_keys = set()  # 用于去重
        
        for code in fund_pool:
            # 排除已持仓
            if code in exclude_codes:
                continue
            
            # 获取历史净值
            nav_list = get_nav_func(code, days=90) if get_nav_func else []
            
            if len(nav_list) < 20:
                continue
            
            # 计算指标
            name = fund_names.get(code, code)
            metrics = self.calculate_metrics(code, name, nav_list)
            
            # ========== 修复：波动率过滤 ==========
            # 动量型策略排除低波动基金（债券/货币类）
            if recommend_type == RecommendType.MOMENTUM:
                if metrics.volatility < MIN_VOLATILITY_FOR_MOMENTUM:
                    continue  # 跳过低波动基金
            
            # ========== 修复：同类基金去重 ==========
            if deduplicate:
                dedup_key = get_dedup_key(code)
                if dedup_key in seen_dedup_keys:
                    continue  # 已见过同类基金，跳过
                seen_dedup_keys.add(dedup_key)
            
            # 计算综合评分
            score = self.calculate_composite_score(metrics, recommend_type)
            
            results.append({
                'code': code,
                'name': name,
                'score': round(score, 1),
                'momentum_20d': round(metrics.momentum_20d, 2),
                'momentum_60d': round(metrics.momentum_60d, 2),
                'momentum_90d': round(metrics.momentum_90d, 2),
                'volatility': round(metrics.volatility * 100, 2),
                'sharpe_ratio': round(metrics.sharpe_ratio, 2),
                'max_drawdown': round(metrics.max_drawdown * 100, 2),
                'risk_score': round(metrics.risk_score, 1),
                'recommend_type': recommend_type.value,
                'analysis_date': nav_list[-1].get('date', '') if nav_list else '',
            })
        
        # 按评分排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:limit]
    
    def find_similar_funds(self, 
                          target_code: str,
                          fund_pool: List[str],
                          fund_names: Dict[str, str],
                          exclude_codes: List[str] = None,
                          limit: int = 5,
                          get_nav_func=None) -> List[Dict]:
        """
        查找与目标基金相似的基金
        
        基于：
        1. 收益率相关性
        2. 波动率相似度
        3. 风险收益特征相似度
        """
        if exclude_codes is None:
            exclude_codes = []
        
        # 获取目标基金数据
        target_nav = get_nav_func(target_code, days=180) if get_nav_func else []
        if len(target_nav) < 30:
            return []
        
        target_metrics = self.calculate_metrics(
            target_code, 
            fund_names.get(target_code, target_code), 
            target_nav
        )
        
        # 计算目标基金的日收益率序列
        target_returns = []
        for i in range(1, len(target_nav)):
            prev_nav = float(target_nav[i-1].get('nav', 0))
            curr_nav = float(target_nav[i].get('nav', 0))
            if prev_nav > 0:
                target_returns.append((curr_nav - prev_nav) / prev_nav)
        
        similar_funds = []
        
        for code in fund_pool:
            if code == target_code or code in exclude_codes:
                continue
            
            nav_list = get_nav_func(code, days=180) if get_nav_func else []
            if len(nav_list) < 30:
                continue
            
            metrics = self.calculate_metrics(code, fund_names.get(code, code), nav_list)
            
            # 计算日收益率序列
            fund_returns = []
            for i in range(1, len(nav_list)):
                prev_nav = float(nav_list[i-1].get('nav', 0))
                curr_nav = float(nav_list[i].get('nav', 0))
                if prev_nav > 0:
                    fund_returns.append((curr_nav - prev_nav) / prev_nav)
            
            # 计算相关性 (使用对齐的收益率序列)
            min_len = min(len(target_returns), len(fund_returns))
            if min_len < 20:
                continue
                
            # 取最近的数据对齐
            t_ret = target_returns[-min_len:]
            f_ret = fund_returns[-min_len:]
            
            # Pearson相关系数
            t_mean = sum(t_ret) / len(t_ret)
            f_mean = sum(f_ret) / len(f_ret)
            
            numerator = sum((t - t_mean) * (f - f_mean) for t, f in zip(t_ret, f_ret))
            t_var = sum((t - t_mean) ** 2 for t in t_ret)
            f_var = sum((f - f_mean) ** 2 for f in f_ret)
            
            denom = math.sqrt(t_var * f_var)
            correlation = numerator / denom if denom > 0 else 0
            
            # 相似度 = 相关性权重 + 波动率相似度 + 收益特征相似度
            vol_similarity = 1 - abs(target_metrics.volatility - metrics.volatility)
            sharpe_similarity = 1 - abs(target_metrics.sharpe_ratio - metrics.sharpe_ratio) / 2
            
            # 综合相似度 (相关性太高反而不好，要有一定分散)
            similarity = (abs(correlation) * 0.4 + 
                         vol_similarity * 0.3 + 
                         sharpe_similarity * 0.3)
            
            similar_funds.append({
                'code': code,
                'name': fund_names.get(code, code),
                'similarity': round(similarity * 100, 1),
                'correlation': round(correlation, 3),
                'momentum_90d': round(metrics.momentum_90d, 2),
                'volatility': round(metrics.volatility * 100, 2),
                'sharpe_ratio': round(metrics.sharpe_ratio, 2),
            })
        
        # 按相似度排序
        similar_funds.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similar_funds[:limit]
    
    def get_portfolio_analysis(self, holdings: List[Dict], get_nav_func) -> Dict:
        """分析持仓组合特征（增强版）"""
        if not holdings:
            return {
                'avg_volatility': 0,
                'avg_sharpe': 0,
                'avg_momentum': 0,
                'diversification_score': 0,
                'risk_level': '未持仓',
                'recommendations': [],
                'portfolio_score': 0,
                'holdings_count': 0,
            }

        all_metrics = []
        nav_lists_map = {}
        for h in holdings:
            nav_list = get_nav_func(h['code'], days=90)
            if len(nav_list) >= 20:
                m = self.calculate_metrics(h['code'], h.get('name', h['code']), nav_list)
                all_metrics.append(m)
                nav_lists_map[h['code']] = nav_list

        if not all_metrics:
            return {
                'avg_volatility': 0,
                'avg_sharpe': 0,
                'avg_momentum': 0,
                'diversification_score': 0,
                'risk_level': '数据不足',
                'recommendations': [],
                'portfolio_score': 0,
                'holdings_count': 0,
            }

        avg_vol = sum(m.volatility for m in all_metrics) / len(all_metrics)
        avg_sharpe = sum(m.sharpe_ratio for m in all_metrics) / len(all_metrics)
        avg_mom = sum(m.momentum_90d for m in all_metrics) / len(all_metrics)

        if avg_vol < 0.15:
            risk_level = "保守型"
        elif avg_vol < 0.25:
            risk_level = "稳健型"
        elif avg_vol < 0.35:
            risk_level = "积极型"
        else:
            risk_level = "激进型"

        codes = list(nav_lists_map.keys())
        if len(codes) >= 2:
            import math
            correlations = []
            for i in range(len(codes)):
                for j in range(i + 1, len(codes)):
                    corr = self._calc_correlation2(nav_lists_map[codes[i]], nav_lists_map[codes[j]])
                    if corr is not None:
                        correlations.append(corr)
            if correlations:
                avg_corr = sum(correlations) / len(correlations)
                diversification_score = max(0, min(100, int((1 - avg_corr) * 100)))
            else:
                diversification_score = 50
        else:
            diversification_score = 60

        sharpe_score = min(30, avg_sharpe * 10)
        vol_score = max(0, 25 - (avg_vol * 100 - 10) * 0.5)
        div_score = diversification_score * 0.2
        mom_score = max(-5, min(10, avg_mom * 0.5))
        count_score = min(10, len(all_metrics) * 2)
        portfolio_score = round(sharpe_score + vol_score + div_score + mom_score + count_score, 1)
        portfolio_score = max(0, min(100, portfolio_score))

        sorted_by_sharpe = sorted(all_metrics, key=lambda x: x.sharpe_ratio, reverse=True)
        best_fund = {'code': sorted_by_sharpe[0].code, 'name': sorted_by_sharpe[0].name, 'sharpe': round(sorted_by_sharpe[0].sharpe_ratio, 2)} if sorted_by_sharpe else None
        worst_fund = {'code': sorted_by_sharpe[-1].code, 'name': sorted_by_sharpe[-1].name, 'sharpe': round(sorted_by_sharpe[-1].sharpe_ratio, 2)} if sorted_by_sharpe else None

        returns_1m = []
        for m in all_metrics:
            r = (m.momentum_20d / 20) * 22 if m.momentum_20d else 0
            returns_1m.append(r)
        avg_return_1m = sum(returns_1m) / len(returns_1m) if returns_1m else 0

        return {
            'avg_volatility': round(avg_vol * 100, 2),
            'avg_sharpe': round(avg_sharpe, 2),
            'avg_momentum': round(avg_mom, 2),
            'diversification_score': diversification_score,
            'risk_level': risk_level,
            'holdings_count': len(all_metrics),
            'portfolio_score': portfolio_score,
            'avg_return_1m': round(avg_return_1m, 2),
            'best_fund': best_fund,
            'worst_fund': worst_fund,
            'correlation_avg': round(sum(correlations) / len(correlations), 3) if correlations else 0,
            'recommendations': [],
        }

    def _calc_correlation2(self, nav_list1: list, nav_list2: list):
        """计算两个净值序列的相关系数"""
        import math
        if len(nav_list1) < 10 or len(nav_list2) < 10:
            return None
        n = min(len(nav_list1), len(nav_list2))
        nav1, nav2 = nav_list1[-n:], nav_list2[-n:]
        prices1 = [h['nav'] for h in nav1]
        prices2 = [h['nav'] for h in nav2]
        returns1 = [(prices1[i] - prices1[i-1]) / prices1[i-1] for i in range(1, n)]
        returns2 = [(prices2[i] - prices2[i-1]) / prices2[i-1] for i in range(1, n)]
        if len(returns1) < 10:
            return None
        mean1 = sum(returns1) / len(returns1)
        mean2 = sum(returns2) / len(returns2)
        cov = sum((returns1[i] - mean1) * (returns2[i] - mean2) for i in range(len(returns1))) / len(returns1)
        std1 = math.sqrt(sum((r - mean1) ** 2 for r in returns1) / len(returns1))
        std2 = math.sqrt(sum((r - mean2) ** 2 for r in returns2) / len(returns2))
        if std1 == 0 or std2 == 0:
            return None
        return cov / (std1 * std2)



# ========== 扩展基金池 (50+只) ==========

# 宽基指数基金
BROAD_INDEX_FUNDS = {
    # 沪深300
    "510300": "沪深300ETF",
    "159919": "沪深300ETF易方达",
    "000961": "天弘沪深300ETF联接A",
    "110020": "易方达沪深300ETF联接A",
    "001143": "嘉实沪深300ETF联接A",
    # 中证500
    "510500": "中证500ETF",
    "000962": "天弘中证500ETF联接A",
    "110026": "易方达创业板ETF联接A",
    # 创业板
    "159915": "创业板ETF",
    "110026": "易方达创业板ETF联接A",
    "001592": "天弘创业板ETF联接A",
    # 科创板
    "588000": "科创50ETF",
    "588050": "科创ETF工银",
    "588080": "科创板50ETF",
    # 上证50/超级蓝筹
    "510050": "上证50ETF",
    "510100": "上证50ETF易方达",
}

# 行业主题基金
INDUSTRY_FUNDS = {
    # 消费
    "110022": "易方达消费行业",
    "000083": "汇添富消费行业混合",
    "270050": "广发消费品精选",
    # 医疗健康
    "001550": "天弘医疗健康混合A",
    "000831": "工银医疗保健股票",
    "420003": "天弘医药混合A",
    "001718": "工银前沿医疗股票A",
    # 新能源
    "001410": "信澳新能源精选混合",
    "001579": "国泰智能汽车股票A",
    "005927": "长城新能源股票A",
    # 科技/半导体
    "001513": "易方达信息行业混合",
    "008281": "银河创新成长混合A",
    "001229": "中邮核心科技混合",
    "006327": "易方达日经225ETF",
    # 金融/银行
    "001694": "华宝券商ETF联接A",
    "004070": "南方中证全指证券",
    # 白酒/食品
    "161725": "招商中证白酒指数A",
    "000869": "易方达食品饮料ETF联接A",
    # 军工
    "001361": "易方达国防军工混合",
    "004698": "博时军工主题股票A",
    # QDII海外
    "000075": "华夏全球科技QDII",
    "501021": "华宝标普美国品质股票",
    "160213": "国泰国证有色金属",
    "013871": "天弘越南市场股票A",
}

# 债券/稳健基金
BOND_FUNDS = {
    "000171": "易方达高等级信用债A",
    "001061": "华夏纯债债券A",
    "000345": "鹏华丰融定期开放债券",
    "217022": "招商产业债券A",
    "003327": "万家鑫璟纯债A",
    "004437": "长城行业轮动混合",
    "110007": "易方达稳健收益债券A",
    "000536": "前海开源可转债债券",
}

# QDII海外基金
QDII_FUNDS = {
    "000075": "华夏全球股票(QDII)",
    "501021": "华宝标普美国品质股票(QDII)",
    "160717": "招商全球商品ETF(QDII)",
    "006327": "易方达日经225ETF(QDII)",
    "008763": "华宝港股通恒生科技指数",
    "013871": "天弘越南市场股票(QDII)",
    "000834": "大成纳斯达克100指数",
    "040046": "华安纳斯达克100指数",
}

# 全部基金池
ALL_FUND_POOL = {
    **BROAD_INDEX_FUNDS,
    **INDUSTRY_FUNDS,
    **BOND_FUNDS,
    **QDII_FUNDS,
}

FUND_CATEGORIES = {
    "broad_index": ("宽基指数", list(BROAD_INDEX_FUNDS.keys())),
    "industry": ("行业主题", list(INDUSTRY_FUNDS.keys())),
    "bond": ("债券稳健", list(BOND_FUNDS.keys())),
    "qdii": ("海外QDII", list(QDII_FUNDS.keys())),
    "all": ("全部基金", list(ALL_FUND_POOL.keys())),
}


def quick_recommend(recommend_type: str = 'momentum',
                    category: str = 'all',
                    exclude_codes: List[str] = None,
                    limit: int = 6,
                    get_nav_func=None,
                    deduplicate: bool = True) -> List[Dict]:
    """
    快速推荐接口
    
    Args:
        recommend_type: 推荐类型 (momentum/contrarian/low_vol/high_sharpe/diversify)
        category: 基金分类 (broad_index/industry/bond/qdii/all)
        exclude_codes: 排除的基金代码
        limit: 返回数量
        get_nav_func: 获取净值数据的函数
        deduplicate: 是否去重（同一指数只保留一只）
    """
    
    rec_type_map = {
        'momentum': RecommendType.MOMENTUM,
        'contrarian': RecommendType.CONTRARIAN,
        'low_vol': RecommendType.LOW_VOLATILITY,
        'high_sharpe': RecommendType.HIGH_SHARPE,
        'diversify': RecommendType.DIVERSIFICATION,
    }
    
    rec_type = rec_type_map.get(recommend_type, RecommendType.MOMENTUM)
    
    # 获取基金池
    fund_list = FUND_CATEGORIES.get(category, FUND_CATEGORIES['all'])[1]
    
    recommender = SmartRecommender()
    
    return recommender.recommend(
        fund_pool=fund_list,
        fund_names=ALL_FUND_POOL,
        exclude_codes=exclude_codes or [],
        recommend_type=rec_type,
        limit=limit,
        get_nav_func=get_nav_func,
        deduplicate=deduplicate,
    )


if __name__ == '__main__':
    # 测试
    print("🧪 智能推荐系统测试")
    print("=" * 50)
    
    recommender = SmartRecommender()
    
    # 模拟数据
    test_nav = [
        {'date': f'2024-01-{i:02d}', 'nav': 1.0 + i * 0.002 + (i % 7) * 0.001}
        for i in range(1, 91)
    ]
    
    metrics = recommender.calculate_metrics('TEST', '测试基金', test_nav)
    print(f"📊 测试基金指标:")
    print(f"   90日动量: {metrics.momentum_90d:.2f}%")
    print(f"   年化波动率: {metrics.volatility * 100:.2f}%")
    print(f"   夏普比率: {metrics.sharpe_ratio:.2f}")
    print(f"   最大回撤: {metrics.max_drawdown * 100:.2f}%")
    
    # 测试各类型推荐
    print("\n📈 各类型推荐模拟评分:")
    for rec_type in RecommendType:
        score = recommender.calculate_composite_score(metrics, rec_type)
        print(f"   {rec_type.value}: {score:.1f}分")
