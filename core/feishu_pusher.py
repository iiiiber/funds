"""飞书推送服务"""
import requests
import pymysql
from datetime import datetime

DB_CONFIG = {
    'host': '127.0.0.1', 'port': 3306, 'user': 'funds', 'password': '6NZ7Hp2Z5YWShARJ', 
    'database': 'funds', 'charset': 'utf8mb4'
}

def get_feishu_settings():
    """获取飞书推送配置"""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT * FROM feishu_settings WHERE id = 1')
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

def should_push(profit_pct: float, condition: str) -> bool:
    """判断是否应该推送"""
    if condition == 'all':
        return True
    elif condition == 'profit':
        return profit_pct > 0
    elif condition == 'loss':
        return profit_pct < 0
    return True

def format_report_message(code: str, name: str, ai_report: str, holding_info: dict = None) -> dict:
    """格式化飞书消息"""
    # 判断盈亏
    profit_pct = holding_info.get('profit_pct', 0) if holding_info else 0
    status_emoji = '📈' if profit_pct >= 0 else '📉'
    status_text = f"盈利{profit_pct:.1f}%" if profit_pct >= 0 else f"亏损{abs(profit_pct):.1f}%"
    
    # 简化报告内容
    lines = ai_report.strip().split('\n')
    brief = []
    current_section = []
    for line in lines:
        if line.startswith('**') and line.endswith('**'):
            if current_section:
                brief.append('  '.join(current_section))
            brief.append(f"【{line.strip('*')}】")
            current_section = []
        elif line.strip():
            current_section.append(line.strip())
    if current_section:
        brief.append('  '.join(current_section))
    
    report_text = '\n'.join(brief[:10])  # 限制行数
    
    message = f"""📊 基金AI分析报告

*【{name}】*（{code}）
{status_emoji} *{status_text}*

{report_text}

─────────────────
📅 {datetime.now().strftime('%Y-%m-%d %H:%M')} | 🤖 FundQuant"""
    
    return {
        'msg_type': 'text',
        'content': {'text': message}
    }

def push_to_feishu(code: str, name: str, ai_report: str, holding_info: dict = None) -> tuple:
    """推送AI报告到飞书群"""
    try:
        settings = get_feishu_settings()
        
        if not settings or not settings.get('webhook_url'):
            return False, '未配置飞书Webhook'
        
        if not settings.get('enabled'):
            return False, '飞书推送未启用'
        
        # 检查推送条件
        profit_pct = holding_info.get('profit_pct', 0) if holding_info else 0
        if not should_push(profit_pct, settings.get('push_condition', 'all')):
            return False, f'不满足推送条件({settings.get("push_condition")})'
        
        # 格式化消息
        payload = format_report_message(code, name, ai_report, holding_info)
        
        # 发送请求
        resp = requests.post(settings['webhook_url'], json=payload, timeout=10)
        result = resp.json()
        
        if resp.status_code == 200 and (result.get('code') == 0 or result.get('StatusCode') == 0):
            return True, '推送成功'
        else:
            return False, f"推送失败: {result}"
    except Exception as e:
        return False, str(e)
