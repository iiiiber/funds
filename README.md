# 📊 FundQuant - 基金量化助手

个人投资者工具，帮助追踪已购基金、获取实时行情、智能推荐潜力基金。

**⚠️ 风险提示**：本工具仅供个人学习参考，不构成投资建议。基金投资有风险，入市需谨慎。

## 功能特性

- 📊 **已买基金追踪** - 管理持仓、实时行情、盈亏计算
- 📈 **量化分析** - 波动率、夏普比率、动量指标
- ⏰ **定时提醒** - 每天自动推送日报到飞书
- 🌐 **Web界面** - 浏览器查看持仓和推荐
- 🔍 **基金搜索** - 热门基金筛选

## 项目结构

```
fundquant/
├── core/               # 核心模块
│   ├── fund_api.py     # 天天基金API
│   ├── holdings.py     # 持仓管理
│   ├── analysis.py      # 量化分析
│   └── notify.py        # 飞书通知
├── app/                # Web应用
│   └── main.py          # Flask服务器
├── scripts/            # 脚本
│   ├── manage.py        # 管理工具
│   ├── daily_report.py  # 日报生成
│   └── install_cron.sh  # 定时任务安装
├── data/               # 数据存储
├── config.yaml         # 配置文件
└── requirements.txt
```

## 快速开始

### 1. 查看持仓

```bash
cd ~/fundquant
python3 scripts/manage.py holdings --list    # 列出持仓
python3 scripts/manage.py status              # 查看状态+盈亏
```

### 2. 管理持仓

```bash
# 添加基金
python3 scripts/manage.py holdings --add 510300 "" 1000 3.8

# 删除基金
python3 scripts/manage.py holdings --remove 510300

# 更新成本价
python3 scripts/manage.py holdings --update 510300 cost=4.0
```

### 3. 生成日报

```bash
python3 scripts/daily_report.py
```

### 4. Web界面

```bash
python3 -m app.web
# 访问 http://localhost:8080
```

### 5. 定时任务

```bash
# 安装定时推送（每天9:30）
./scripts/install_cron.sh

# 自定义时间（如14:00）
./scripts/install_cron.sh 14:00

# 移除定时任务
./scripts/install_cron.sh --remove
```

## 飞书通知配置

在 `config.yaml` 中添加：

```yaml
notification:
  feishu:
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/你的webhook"
```

或者在飞书群中添加自定义机器人获取 Webhook。

## 数据来源

所有数据均来自东方财富天天基金公开 API：
- 实时行情：`fundgz.1234567.com.cn`
- 历史净值：`api.fund.eastmoney.com/f10/lsjz`

⚠️ 仅供参考，不构成投资建议。
