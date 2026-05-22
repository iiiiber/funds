#!/bin/bash
cd /www/wwwroot/funds.imoons.cn/app
pkill -f 'python web_new.py' 2>/dev/null
sleep 1
nohup /www/wwwroot/funds.imoons.cn/venv/bin/python web_new.py > /tmp/flask.log 2>&1 &
echo "Flask started on port 8080"
