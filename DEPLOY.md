# 📊 FundQuant 部署指南

基金量化助手 - 持仓追踪 / 智能推荐 / AI分析

## 功能特性

- 📊 **已买基金追踪** - 管理持仓、实时行情、盈亏计算
- 📈 **量化分析** - 波动率、夏普比率、动量指标、估值分析
- 🤖 **AI智能分析** - 多模型支持（DeepSeek/MiniMax/Gemini）
- ⏰ **定时提醒** - 持仓止盈止损提醒 + 每日行情推送
- 🌐 **Web界面** - 浏览器查看持仓、推荐、市场分析
- 🔍 **基金筛选** - 热门基金多维度筛选

## 环境要求

- Ubuntu 20.04+ / CentOS 7+
- Python 3.9+
- MySQL 5.7+ 或 MariaDB 10.3+
- Nginx
- Git

## 一键部署

```bash
# 1. 克隆代码
git clone https://github.com/iiiiber/funds.git
cd funds

# 2. 安装依赖
pip install -r requirements.txt

# 3. 创建数据库（MySQL）
mysql -u root -p
CREATE DATABASE funds DEFAULT CHARACTER SET utf8mb4;
CREATE USER 'funds'@'localhost' IDENTIFIED BY '你的密码';
GRANT ALL PRIVILEGES ON funds.* TO 'funds'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# 4. 导入数据库结构
mysql -u funds -p funds < admin/init_db.sql

# 5. 修改配置
cp config.yaml.example config.yaml
# 编辑 config.yaml，填入数据库密码和API密钥

# 6. 启动服务
bash start_flask.sh
```

## 手动部署

### 1. 安装Python依赖

```bash
pip install flask flask-cors akshare pandas numpy
pip install pymysql cryptography openai
```

### 2. 配置Nginx

```nginx
server {
    listen 80;
    server_name funds.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. 配置SSL（可选）

```bash
certbot --nginx -d funds.example.com
```

### 4. 启动服务

```bash
# 主站（8080）
python -m app.main &

# 管理后台（8081）
python admin/admin.py &
```

## 定时任务

### 持仓提醒（每个工作日 15:10）

```bash
# 编辑 crontab
crontab -e

# 添加行
10 15 * * 1-5 cd /path/to/funds && python scripts/alert_check.py >> logs/alert.log 2>&1
```

### 每日推送（每天 20:00）

```bash
0 20 * * * cd /path/to/funds && python scripts/daily_report.py >> logs/daily.log 2>&1
```

## 目录结构

```
funds/
├── app/                    # 主站前端
│   ├── main.py            # Flask主程序
│   └── templates/         # 前端模板
├── admin/                  # 管理后台
│   ├── admin.py           # 管理后台入口
│   ├── models/            # 数据模型
│   ├── routes/            # 路由
│   └── templates/         # 管理后台模板
├── core/                   # 核心业务逻辑
│   ├── fund_api.py       # 天天基金API
│   ├── holdings.py       # 持仓管理
│   ├── analysis.py       # 量化分析
│   ├── enhanced_analyzer.py # AI增强分析
│   └── notify.py         # 飞书通知
├── scripts/               # 定时脚本
│   ├── alert_check.py    # 持仓提醒
│   └── daily_report.py   # 日报生成
├── data/                  # 数据存储
├── config.yaml            # 配置文件
├── requirements.txt       # 依赖
└── start_flask.sh        # 启动脚本
```

## 访问地址

- **主站：** http://localhost:8080
- **管理后台：** http://localhost:8081/admin/
- **默认账号：** admin / admin123（部署后请修改）

## 常见问题

### 1. 数据库连接失败

检查 MySQL 服务状态：
```bash
systemctl status mysql
```

测试连接：
```bash
mysql -u funds -p funds
```

### 2. AI分析不可用

确保 `config.yaml` 中的 `MINIMAX_API_KEY` 已正确配置。

### 3. 页面空白

检查 Flask 是否正常运行：
```bash
ps aux | grep python
```

查看日志：
```bash
tail -f flask.log
```

## 数据来源

所有数据均来自东方财富天天基金公开API：
- 实时行情：`fundgz.1234567.com.cn`
- 历史净值：`api.fund.eastmoney.com/f10/lsjz`

---

**⚠️ 风险提示**：本工具仅供个人学习参考，不构成投资建议。基金投资有风险，入市需谨慎。