#!/usr/bin/env python3
"""同步持仓数据到数据库"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import FundDB
from core.holdings import HoldingsManager

def main():
    db = FundDB()
    mgr = HoldingsManager()
    
    # 从 JSON 获取持仓
    holdings = mgr.list()
    
    print(f"同步 {len(holdings)} 条持仓到数据库...")
    
    for h in holdings:
        # 检查是否已存在
        existing = db.get_holdings()
        existing_codes = [x['code'] for x in existing]
        
        if h['code'] in existing_codes:
            print(f"  ⏭️  {h['code']} 已存在，跳过")
        else:
            db.add_holding(
                h['code'],
                h.get('name', ''),
                h.get('shares', 0),
                h.get('cost', 0),
                h.get('note', '')
            )
            print(f"  ✅ 添加 {h['code']} {h.get('name', '')}")
    
    print(f"\n当前数据库持仓:")
    for h in db.get_holdings():
        print(f"  {h['code']} {h['name']} - 成本 {h['cost']}")

if __name__ == '__main__':
    main()
