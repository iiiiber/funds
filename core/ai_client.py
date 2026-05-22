"""可配置的AI客户端 - 支持多种后端"""
import os
import sys
import logging
from pathlib import Path
from typing import Optional, List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.fund_analyzer import FundAnalyzer
from core.ai_model_manager import ai_model_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


class AIClient:
    """可配置的AI客户端"""
    
    def __init__(self, model_id: int = None):
        """
        初始化AI客户端
        model_id: 指定模型ID，不指定则使用默认模型
        """
        self.model_id = model_id
        self.fund_analyzer = FundAnalyzer()
        self._load_model()
    
    def _load_model(self):
        """从数据库加载模型配置"""
        if self.model_id:
            config = ai_model_manager.get_model_by_id(self.model_id)
        else:
            config = ai_model_manager.get_default_model()
        
        if not config:
            logger.warning("未找到AI模型配置")
            self.config = None
            return
        
        self.config = config
        logger.info(f"AI客户端已加载: {config.get('name')} ({config.get('model_id')})")
    
    def chat(self, messages: list, temperature: float = None) -> Optional[str]:
        """调用AI接口"""
        if not self.config:
            return None
        
        import requests
        
        api_key = self.config.get('api_key', '')
        if not api_key:
            logger.error("API密钥为空")
            return None
        
        api_url = self.config.get('api_url', '')
        model_id = self.config.get('model_id', '')
        temp = temperature if temperature is not None else float(self.config.get('temperature', 0.5))
        timeout = int(self.config.get('timeout', 30))
        max_tokens = int(self.config.get('max_tokens', 300))
        
        # 构建消息
        prompt = messages[-1].get('content', '') if messages else ''
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temp,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=data, timeout=timeout)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('content', [])
                for item in content:
                    if item.get('type') == 'text':
                        return item.get('text', '').strip()
                logger.warning("API响应无text内容")
                return None
            else:
                logger.error(f"AI API错误: {response.status_code} - {response.text[:200]}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("AI请求超时")
            return None
        except Exception as e:
            logger.error(f"AI请求失败: {e}")
            return None


class FundAIAnalyzer:
    """AI基金分析器 - 使用可配置AI客户端"""
    
    def __init__(self, model_id: int = None):
        self.client = AIClient(model_id=model_id)
        self.fund_analyzer = FundAnalyzer()
    
    def _get_technical_indicators(self, hist: list) -> Dict:
        """计算技术指标"""
        if not hist or len(hist) < 20:
            return {}
        
        closes = [float(h.get('nav', h.get('accum_nav', 0))) for h in hist]
        prices = [float(h.get('accum_nav', h.get('nav', 0))) for h in hist]
        
        # 简单计算
        ma5 = sum(prices[-5:]) / 5 if len(prices) >= 5 else prices[-1]
        ma10 = sum(prices[-10:]) / 10 if len(prices) >= 10 else ma5
        ma20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else ma10
        
        current = prices[-1]
        
        return {
            'current': current,
            'ma5': round(ma5, 4),
            'ma10': round(ma10, 4),
            'ma20': round(ma20, 4),
            'change_5d': round((current - closes[-6]) / closes[-6] * 100, 2) if len(closes) >= 6 else 0,
            'change_20d': round((current - closes[-21]) / closes[-21] * 100, 2) if len(closes) >= 21 else 0
        }
    
    def analyze_fund(self, code: str) -> Dict:
        """分析基金并生成报告"""
        # 获取历史数据
        from core.fund_api import get_historical_nav
        
        hist = get_historical_nav(code)
        indicators = self._get_technical_indicators(hist) if hist else {}
        
        # 构建提示词
        prompt = f"""请分析基金代码 {code}，近期表现如下：
- 当前净值: {indicators.get('current', 'N/A')}
- 5日均线: {indicators.get('ma5', 'N/A')}
- 10日均线: {indicators.get('ma10', 'N/A')}
- 20日均线: {indicators.get('ma20', 'N/A')}
- 5日涨跌: {indicators.get('change_5d', 'N/A')}%
- 20日涨跌: {indicators.get('change_20d', 'N/A')}%

请给出简要分析和建议（100字以内）。"""
        
        # 调用AI
        response = self.client.chat([{'role': 'user', 'content': prompt}])
        
        return {
            'code': code,
            'indicators': indicators,
            'analysis': response or 'AI分析暂时不可用'
        }
    
    def batch_analyze(self, codes: List[str]) -> List[Dict]:
        """批量分析"""
        return [self.analyze_fund(code) for code in codes]


# 向后兼容
MiniMaxAI = AIClient


if __name__ == '__main__':
    # 测试
    analyzer = FundAIAnalyzer()
    result = analyzer.analyze_fund('510300')
    print(result)
