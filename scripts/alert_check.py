#!/usr/bin/env python3
"""
持仓盈亏提醒检查脚本
- 检查所有持仓的盈亏状态
- 达到止盈/止损阈值且今日未提醒则发送飞书通知
- 建议在收盘后(15:00-15:30)运行
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pymysql
import requests
from datetime import datetime, date

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'funds',
    'password': '6NZ7Hp2Z5YWShARJ',
    'database': 'funds',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_feishu_webhook():
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT webhook_url FROM feishu_settings WHERE id=1 AND enabled=1")
    row = cur.fetchone()
    conn.close()
    return row['webhook_url'] if row else None

def send_feishu(msg):
    webhook = get_feishu_webhook()
    if not webhook:
        print('Feishu webhook not configured or disabled')
        return False
    try:
        resp = requests.post(webhook, json={
            'msg_type': 'text',
            'content': {'text': msg}
        }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print('Feishu send error:', e)
        return False

def reset_alert_sent():
    """每天重置所有 alert_sent_today 为 0（跨过午夜后首次执行时）"""
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    # 检查是否有记录需要重置（alert_sent_date 不是今天）
    today = date.today()
    cur.execute("SELECT COUNT(*) as c FROM holdings WHERE alert_sent_today = 1 AND (alert_sent_date IS NULL OR alert_sent_date != %s)", (today,))
    row = cur.fetchone()
    count = row['c'] if row else 0
    if count > 0:
        cur.execute("UPDATE holdings SET alert_sent_today = 0 WHERE alert_sent_today = 1 AND (alert_sent_date IS NULL OR alert_sent_date != %s)", (today,))
        conn.commit()
        print(f'Reset {count} holdings alert_sent_today to 0')
    conn.close()
    return count

def check_alerts():
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 获取设置了提醒阈值的持仓
    cur.execute("""
        SELECT id, code, name, shares, cost, nav, amount, profit, profit_pct,
               alert_profit_pct, alert_loss_pct, alert_sent_today, alert_sent_date
        FROM holdings
        WHERE status=1
          AND (alert_profit_pct IS NOT NULL OR alert_loss_pct IS NOT NULL)
    """)
    holdings = cur.fetchall()

    today = date.today()
    alerts_sent = []

    for h in holdings:
        code = h['code']
        name = h['name']
        profit_pct = float(h['profit_pct']) if h['profit_pct'] else 0.0
        profit = float(h['profit']) if h['profit'] else 0.0
        shares = float(h['shares']) if h['shares'] else 0.0
        cost = float(h['cost']) if h['cost'] else 0.0
        alert_profit = float(h['alert_profit_pct']) if h['alert_profit_pct'] else None
        alert_loss = float(h['alert_loss_pct']) if h['alert_loss_pct'] else None
        sent_today = h['alert_sent_today'] == 1 and h['alert_sent_date'] == today

        if sent_today:
            continue

        msg = None

        # 止盈检查
        if alert_profit and profit_pct >= alert_profit:
            msg = f"🎯 【止盈提醒】\n{h['name']} ({code})\n当前收益率: {profit_pct:+.2f}%\n持仓金额: {h['amount']:.2f}元\n已盈: {profit:+.2f}元\n达到止盈线 {alert_profit}%！"

        # 止损检查
        elif alert_loss and profit_pct <= -alert_loss:
            msg = f"🛑 【止损提醒】\n{h['name']} ({code})\n当前收益率: {profit_pct:+.2f}%\n持仓金额: {h['amount']:.2f}元\n已亏: {profit:+.2f}元\n触及止损线 {alert_loss}%！"

        if msg:
            ok = send_feishu(msg)
            if ok:
                alerts_sent.append(code)
                # 重置提醒状态
                cur.execute("""
                    UPDATE holdings
                    SET alert_sent_today = 1, alert_sent_date = %s
                    WHERE id = %s
                """, (today, h['id']))

    conn.commit()
    conn.close()

    if alerts_sent:
        print(f'Alerts sent for: {alerts_sent}')
    else:
        print('No alerts triggered today')

if __name__ == '__main__':
    # 每天首次执行时重置所有 alert_sent_today
    reset_alert_sent()
    check_alerts()
