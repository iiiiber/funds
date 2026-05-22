#!/usr/bin/env python3
"""智能推荐定时任务 - 使用新版SmartRecommender"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime

from core.smart_recommender import SmartRecommender

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/recommendation.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def main():
    """生成智能推荐"""
    logger.info("=" * 60)
    logger.info(f"📊 FundQuant 智能推荐更新 [{datetime.now()}]")
    logger.info("=" * 60)
    
    try:
        recommender = SmartRecommender(max_workers=5)
        result = recommender.save_recommendations()
        
        # 统计
        total_funds = sum(
            len(s.get('funds', [])) 
            for s in result.get('strategies', {}).values()
        )
        
        hot_sectors = result.get('hot_sectors', [])
        
        logger.info(f"✅ 推荐更新完成")
        logger.info(f"   热点板块: {[s['sector'] for s in hot_sectors[:5]]}")
        logger.info(f"   推荐基金: {total_funds} 只")
        
        for strategy, data in result.get('strategies', {}).items():
            logger.info(f"   • {data.get('name', strategy)}: {len(data.get('funds', []))} 只")
        
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 推荐更新失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
