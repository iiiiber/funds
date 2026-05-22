#!/usr/bin/env python3
import sys, json, urllib.parse
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.fund_api import get_realtime_quote, get_historical_nav
from core.holdings import HoldingsManager

DATA_DIR = Path(__file__).parent.parent / 'data'
ACTUAL_NAV_FILE = DATA_DIR / 'actual_navs.json'

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        if p.path == '/': self.serve_index()
        elif p.path == '/api/quotes': self.serve_quotes()
        elif p.path == '/api/popular': self.serve_popular()
        else: super().do_GET()
    
    def serve_index(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(self.get_html().encode('utf-8'))
    
    def serve_quotes(self):
        mgr = HoldingsManager()
        holdings = mgr.list()
        actual_navs = {}
        if ACTUAL_NAV_FILE.exists():
            with open(ACTUAL_NAV_FILE, 'r') as f:
                actual_navs = json.load(f)
        
        results = []
        for h in holdings:
            q = get_realtime_quote(h['code'])
            if q:
                cost = h.get('cost', 0)
                est_nav = q.get('estimated_nav', 0)
                est_chg = q.get('change_pct', 0)
                act = actual_navs.get(h['code'], {})
                act_nav = act.get('nav', 0)
                act_chg = act.get('daily_return', 0) or 0
                act_date = act.get('date', '')
                
                hist = get_historical_nav(h['code'], 5)
                yes_nav = hist[-2].get('nav', 0) if len(hist) >= 2 else 0
                
                disp_nav = act_nav if act_nav > 0 else est_nav
                profit = ((disp_nav - cost) / cost * 100) if cost > 0 else 0
                
                results.append({
                    'code': h['code'], 'name': h['name'], 'cost': cost,
                    'current_nav': disp_nav, 'estimated_nav': est_nav,
                    'actual_nav': act_nav, 'yesterday_nav': yes_nav,
                    'estimated_change': round(est_chg, 2),
                    'actual_change': round(act_chg, 2),
                    'actual_date': act_date,
                    'profit_pct': round(profit, 2),
                    'update_time': q.get('update_time', ''),
                })
        self.send_json(results)
    
    def serve_popular(self):
        from core.fund_api import POPULAR_FUNDS
        r = []
        for c, n in POPULAR_FUNDS.items():
            q = get_realtime_quote(c)
            if q: r.append({'code': c, 'name': n, 'price': q['price'], 'change_pct': q['change_pct']})
        self.send_json(r)
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def get_html(self):
        return open(Path(__file__).parent / 'template_new.html', 'r', encoding='utf-8').read()

def run(port=8080):
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('-p', '--port', type=int, default=8080)
    run(p.parse_args().port)
