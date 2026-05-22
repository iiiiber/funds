"""飞书通知模块"""
import json
import logging
from typing import List, Dict, Optional
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)


class FeishuNotifier:
    """飞书 Webhook 通知"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or self._load_webhook()
    
    def _load_webhook(self) -> Optional[str]:
        """从配置文件加载 webhook"""
        import yaml
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('notification', {}).get('feishu', {}).get('webhook_url')
        except Exception:
            return None
    
    def send(self, message: str, msg_type: str = "text") -> bool:
        """
        发送消息到飞书
        
        Args:
            message: 消息内容
            msg_type: 消息类型 (text/markdown)
        
        Returns:
            bool: 是否发送成功
        """
        if not self.webhook_url:
            logger.warning("飞书 webhook 未配置")
            return False
        
        payload = {
            "msg_type": msg_type,
            "content": {
                "text": message
            }
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                if result.get('code') == 0:
                    logger.info("飞书消息发送成功")
                    return True
                else:
                    logger.error(f"飞书发送失败: {result}")
                    return False
        except Exception as e:
            logger.error(f"飞书通知异常: {e}")
            return False
    
    def send_fund_report(self, holdings: List[Dict], quotes: List[Dict]) -> bool:
        """
        发送基金日报
        
        Args:
            holdings: 持仓列表
            quotes: 行情数据
        """
        # 合并数据
        quote_map = {q.get('code'): q for q in quotes}
        
        lines = ["📊 **FundQuant 基金日报**\n"]
        lines.append(f"📅 {self._today()}\n\n")
        
        total_profit = 0
        total_cost = 0
        
        for h in holdings:
            q = quote_map.get(h['code'], {})
            if not q:
                continue
            
            nav = q.get('current_nav', 0) or q.get('price', 0)
            cost = h.get('cost', 0)
            shares = h.get('shares', 0)
            
            if cost > 0 and shares > 0:
                profit = (nav - cost) * shares
                profit_pct = (nav - cost) / cost * 100
                total_profit += profit
                total_cost += cost * shares
                
                emoji = "🟢" if profit >= 0 else "🔴"
                sign = "+" if profit >= 0 else ""
                
                lines.append(f"{emoji} **{h['name']}**\n")
                lines.append(f"   净值: {nav:.4f} ({q.get('change_pct', 0):+.2f}%)\n")
                lines.append(f"   盈亏: {sign}{profit:.2f}元 ({sign}{profit_pct:.2f}%)\n\n")
        
        # 汇总
        if total_cost > 0:
            total_profit_pct = total_profit / total_cost * 100
            sign = "+" if total_profit >= 0 else ""
            lines.append("───────────────\n")
            lines.append(f"💰 总盈亏: {sign}{total_profit:.2f}元 ({sign}{total_profit_pct:.2f}%)\n")
        
        lines.append(f"\n🤖 via FundQuant")
        
        return self.send(''.join(lines), msg_type="markdown")
    
    def _today(self) -> str:
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M')


# 测试
if __name__ == '__main__':
    notifier = FeishuNotifier()
    
    test_holdings = [
        {'code': '510300', 'name': '沪深300ETF', 'shares': 1000, 'cost': 3.8},
    ]
    
    test_quotes = [
        {'code': '510300', 'current_nav': 4.5758, 'change_pct': 1.54},
    ]
    
    print("📤 测试发送...")
    # notifier.send_fund_report(test_holdings, test_quotes)
    print("✅ 飞书通知模块已就绪")
