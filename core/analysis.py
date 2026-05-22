"""基金量化分析工具"""
import math
from typing import List, Dict


def calculate_volatility(nav_list: List[Dict]) -> float:
    """
    计算基金波动率（基于日收益率标准差）
    
    Args:
        nav_list: 历史净值列表
    
    Returns:
        float: 年化波动率 (如 0.15 表示 15%)
    """
    if len(nav_list) < 2:
        return 0.0
    
    returns = []
    for i in range(1, len(nav_list)):
        prev_nav = float(nav_list[i-1].get('nav', 0))
        curr_nav = float(nav_list[i].get('nav', 0))
        if prev_nav > 0:
            ret = (curr_nav - prev_nav) / prev_nav
            returns.append(ret)
    
    if len(returns) < 2:
        return 0.0
    
    # 计算标准差
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(variance)
    
    # 年化（假设252个交易日）
    annual_std = std * math.sqrt(252)
    return annual_std


def calculate_sharpe_ratio(nav_list: List[Dict], risk_free_rate: float = 0.03) -> float:
    """
    计算夏普比率
    
    Sharpe = (年化收益 - 无风险利率) / 年化波动率
    """
    if len(nav_list) < 2:
        return 0.0
    
    # 计算年化收益
    first_nav = float(nav_list[0].get('nav', 1))
    last_nav = float(nav_list[-1].get('nav', 1))
    days = len(nav_list) - 1
    
    if first_nav <= 0 or days <= 0:
        return 0.0
    
    total_return = (last_nav - first_nav) / first_nav
    annual_return = (1 + total_return) ** (252 / days) - 1
    
    volatility = calculate_volatility(nav_list)
    if volatility == 0:
        return 0.0
    
    sharpe = (annual_return - risk_free_rate) / volatility
    return sharpe


def calculate_max_drawdown(nav_list: List[Dict]) -> float:
    """
    计算最大回撤
    
    Returns:
        float: 最大回撤比例 (正数，如 0.1 表示 10% 回撤)
    """
    if len(nav_list) < 2:
        return 0.0
    
    nav_values = [float(n.get('nav', 0)) for n in nav_list]
    peak = nav_values[0]
    max_dd = 0.0
    
    for nav in nav_values:
        if nav > peak:
            peak = nav
        dd = (peak - nav) / peak
        if dd > max_dd:
            max_dd = dd
    
    return max_dd


def calculate_momentum(nav_list: List[Dict], periods: List[int] = [20, 60, 90]) -> Dict[int, float]:
    """
    计算动量指标（不同周期涨跌幅）
    
    Args:
        nav_list: 历史净值列表
        periods: 周期列表 [20日, 60日, 90日]
    
    Returns:
        Dict: {周期: 涨跌幅%}
    """
    if len(nav_list) < 2:
        return {p: 0.0 for p in periods}
    
    latest_nav = float(nav_list[-1].get('nav', 0))
    result = {}
    
    for period in periods:
        if len(nav_list) > period:
            past_nav = float(nav_list[-period-1].get('nav', 0))
            if past_nav > 0:
                momentum = (latest_nav - past_nav) / past_nav * 100
                result[period] = momentum
            else:
                result[period] = 0.0
        else:
            result[period] = 0.0
    
    return result


def analyze_fund(code: str, nav_list: List[Dict]) -> Dict:
    # 反转净值列表（数据源是倒序的）
    nav_list = list(reversed(nav_list))
    """
    综合分析基金
    
    Returns:
        Dict: 包含各项指标的分析结果
    """
    if not nav_list:
        return {'code': code, 'error': '无数据'}
    
    volatility = calculate_volatility(nav_list)
    sharpe = calculate_sharpe_ratio(nav_list)
    max_dd = calculate_max_drawdown(nav_list)
    momentum = calculate_momentum(nav_list)
    
    # 风险评分 (0-100，越高风险越大)
    risk_score = min(100, int(volatility * 500))
    
    # 收益评分 (基于近90日动量)
    momentum_score = momentum.get(90, 0)
    
    return {
        'code': code,
        'name': nav_list[0].get('name', code),
        'volatility': round(volatility * 100, 2),  # 转为百分比
        'sharpe_ratio': round(sharpe, 2),
        'max_drawdown': round(max_dd * 100, 2),
        'momentum_20d': round(momentum.get(20, 0), 2),
        'momentum_60d': round(momentum.get(60, 0), 2),
        'momentum_90d': round(momentum.get(90, 0), 2),
        'risk_score': risk_score,
        'analysis_date': nav_list[-1].get('date', ''),
    }


if __name__ == '__main__':
    # 测试数据
    test_nav = [
        {'date': '2024-01-01', 'nav': 1.0},
        {'date': '2024-01-02', 'nav': 1.01},
        {'date': '2024-01-03', 'nav': 1.005},
        {'date': '2024-01-04', 'nav': 1.02},
        {'date': '2024-01-05', 'nav': 1.015},
    ]
    
    print("📊 波动率:", calculate_volatility(test_nav))
    print("📈 夏普比率:", calculate_sharpe_ratio(test_nav))
    print("📉 最大回撤:", calculate_max_drawdown(test_nav))
    print("⚡ 动量:", calculate_momentum(test_nav))
