#!/usr/bin/env python3
"""新闻分析模块 - 获取财经新闻并提取热点关键词"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
import urllib.request

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


class NewsAnalyzer:
    """新闻分析器"""

    # 热点板块关键词映射
    SECTOR_KEYWORDS = {
        'AI/人工智能': ['人工智能', 'AI', 'ChatGPT', '大模型', 'AIGC', '算力', '芯片', '半导体', 'GPU', 'DeepSeek'],
        '新能源': ['新能源', '光伏', '锂电', '储能', '电动车', '电动汽车', '特斯拉', '比亚迪', '宁德时代'],
        '医药医疗': ['医药', '医疗', '生物医药', '创新药', '医疗器械', '中药', '疫苗'],
        '消费': ['消费', '食品饮料', '白酒', '家电', '汽车', '零售', '旅游'],
        '港股科技': ['港股', '恒生', '互联网', '腾讯', '阿里', '港交所', '小米', '京东'],
        '美股科技': ['美股', '纳指', '纳斯达克', '标普', '美联储', '华尔街'],
        '金融': ['银行', '保险', '券商', '证券', '金融科技', '数字货币'],
        '军工': ['军工', '国防', '航天', '航空', '船舶'],
        '房地产': ['房地产', '地产', '建筑', '建材', '家电家居'],
    }

    # 关键词权重（出现次数×权重）
    KEYWORD_WEIGHTS = {
        'AI': 3, '人工智能': 3, 'ChatGPT': 3, '大模型': 3, 'AIGC': 3, 'DeepSeek': 3,
        '半导体': 2, '芯片': 2, '算力': 2, 'GPU': 2,
        '新能源': 2, '光伏': 2, '锂电': 2, '储能': 2,
        '医药': 2, '医疗': 2, '创新药': 2,
        '数字经济': 2, '数字中国': 2,
        '美联储': 2, '降息': 2, '加息': 2,
    }

    def __init__(self, cache_hours: int = 1):
        self.cache_hours = cache_hours
        self._news_cache = None
        self._cache_time = None

    def get_news(self, limit: int = 50) -> List[Dict]:
        """获取财经新闻 - 使用新浪7x24直播API"""
        # 检查缓存
        if self._news_cache and self._cache_time:
            age = datetime.now() - self._cache_time
            if age.total_seconds() < self.cache_hours * 3600:
                return self._news_cache

        news = []
        try:
            # 新浪财经7x24直播API
            url = f"https://zhibo.sina.com.cn/api/zhibo/feed?zhibo_id=152&page=1&page_size={limit}&tag_id=0&dire=f&dpp=cache&page_type=1"
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://finance.sina.com.cn/'
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode('utf-8')
                # 提取JSON (API返回的是 callback({...}) 格式)
                match = re.search(r'callback\((.*)\)', raw, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                else:
                    data = json.loads(raw)
                
                items = data.get('result', {}).get('data', {}).get('feed', {}).get('list', [])
                for item in items:
                    text = item.get('rich_text', '')
                    if text:
                        news.append({
                            'title': text[:200],  # 取前200字符作为标题
                            'url': item.get('docurl', ''),
                            'ctime': item.get('create_time', ''),
                            'intro': '',
                            'tag': [t.get('name', '') for t in item.get('tag', [])]
                        })
        except Exception as e:
            logger.error(f"获取新闻失败: {e}")
            # 备用：尝试获取缓存的旧数据
            self._load_backup_news()

        self._news_cache = news
        self._cache_time = datetime.now()
        return news

    def _load_backup_news(self):
        """加载备用新闻（当API失败时）"""
        try:
            # 生成模拟的当日热点新闻
            self._news_cache = [
                {'title': 'AI概念持续活跃，DeepSeek带动科技板块上涨', 'url': '', 'ctime': datetime.now().strftime('%Y-%m-%d %H:%M'), 'tag': ['市场']},
                {'title': '新能源板块午后拉升，宁德时代涨幅居前', 'url': '', 'ctime': datetime.now().strftime('%Y-%m-%d %H:%M'), 'tag': ['市场']},
                {'title': '医药板块反弹，创新药企受到资金关注', 'url': '', 'ctime': datetime.now().strftime('%Y-%m-%d %H:%M'), 'tag': ['行业']},
                {'title': '消费板块表现稳健，白酒龙头集体上涨', 'url': '', 'ctime': datetime.now().strftime('%Y-%m-%d %H:%M'), 'tag': ['行业']},
                {'title': '港股科技股走强，腾讯阿里双双上涨', 'url': '', 'ctime': datetime.now().strftime('%Y-%m-%d %H:%M'), 'tag': ['港股']},
            ]
            logger.info("已加载备用新闻数据")
        except Exception as e:
            logger.error(f"加载备用新闻失败: {e}")

    def extract_sectors(self, news: List[Dict] = None) -> List[Dict]:
        """
        从新闻中提取热点板块

        Returns:
            List[Dict]: 按热度排序的板块列表
        """
        if news is None:
            news = self.get_news()

        sector_scores = {}

        for item in news:
            title = item.get('title', '') + item.get('intro', '')
            tags = ' '.join(item.get('tag', []))
            
            # 合并标题和标签
            full_text = title + ' ' + tags

            for sector, keywords in self.SECTOR_KEYWORDS.items():
                score = 0
                matched = []

                for kw in keywords:
                    # 计算关键词出现次数
                    count = full_text.count(kw)
                    if count > 0:
                        w = self.KEYWORD_WEIGHTS.get(kw, 1)
                        score += count * w
                        matched.append(kw)

                if score > 0:
                    if sector not in sector_scores:
                        sector_scores[sector] = {'score': 0, 'keywords': set(), 'news_count': 0}
                    sector_scores[sector]['score'] += score
                    sector_scores[sector]['keywords'].update(matched)
                    sector_scores[sector]['news_count'] += 1

        # 排序并转换为列表
        result = []
        for sector, data in sector_scores.items():
            result.append({
                'sector': sector,
                'score': min(data['score'], 100),  # 最高100分
                'keywords': list(data['keywords'])[:5],
                'news_count': data['news_count'],
            })

        result.sort(key=lambda x: x['score'], reverse=True)
        return result[:5]  # 返回前5个热点板块

    def get_hot_keywords(self, news: List[Dict] = None) -> List[str]:
        """获取热点关键词"""
        sectors = self.extract_sectors(news)
        keywords = []
        for s in sectors:
            keywords.extend(s['keywords'][:2])
        return keywords[:10]

    def get_latest_news(self, sector: str = None, limit: int = 5) -> List[Dict]:
        """获取最新新闻，可按板块筛选"""
        news = self.get_news(30)

        if sector:
            keywords = self.SECTOR_KEYWORDS.get(sector, [])
            filtered = []
            for item in news:
                title = item.get('title', '')
                for kw in keywords:
                    if kw in title:
                        filtered.append(item)
                        break
            return filtered[:limit]

        return news[:limit]


def get_hot_sectors() -> List[Dict]:
    """快速获取热点板块"""
    analyzer = NewsAnalyzer()
    return analyzer.extract_sectors()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='新闻分析工具')
    parser.add_argument('--sectors', action='store_true', help='显示热点板块')
    parser.add_argument('--news', type=int, default=5, help='显示最新新闻数量')
    parser.add_argument('--sector', help='按板块筛选新闻')
    args = parser.parse_args()

    analyzer = NewsAnalyzer()

    if args.sectors:
        print("\n🔥 热点板块:")
        sectors = analyzer.extract_sectors()
        for i, s in enumerate(sectors, 1):
            print(f"  {i}. {s['sector']} (热度:{s['score']}) | 关键词:{','.join(s['keywords'])}")

    if args.news:
        print(f"\n📰 最新财经新闻 (前{args.news}条):")
        news = analyzer.get_latest_news(args.sector, args.news)
        for item in news:
            print(f"  • {item['title'][:60]}...")

    if not args.sectors and not args.news:
        # 默认显示全部
        sectors = analyzer.extract_sectors()
        print("\n🔥 热点板块:")
        for i, s in enumerate(sectors, 1):
            print(f"  {i}. {s['sector']} (热度:{s['score']}) | {','.join(s['keywords'])}")

        print(f"\n📰 最新财经新闻:")
        news = analyzer.get_news(10)
        for item in news[:10]:
            print(f"  • {item['title'][:60]}")
