#!/usr/bin/env python3
"""测试新闻API"""
import urllib.request
import json

# 测试多个新闻源
apis = [
    ("新浪财经", "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&num=10&page=1"),
    ("东方财富", "https://newsapi.eastmoney.com/kuaixun/v1/getlist_101_ajaxResult_50_1_.html"),
]

for name, url in apis:
    print(f"\n=== 测试 {name} ===")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"成功! 数据长度: {len(str(data))}")
            print(str(data)[:300])
    except Exception as e:
        print(f"失败: {e}")
