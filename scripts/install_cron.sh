#!/bin/bash
# FundQuant 定时任务安装脚本
# 
# 使用方法:
#   ./scripts/install_cron.sh          # 安装每日9:30推送
#   ./scripts/install_cron.sh 14:00     # 自定义时间
#   ./scripts/install_cron.sh --remove  # 移除定时任务

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CRON_SCRIPT="$PROJECT_DIR/scripts/daily_report.py"
LOG_FILE="$PROJECT_DIR/data/cron.log"

# 默认时间
SCHEDULE_TIME="${1:-09:30}"

if [ "$1" == "--remove" ]; then
    echo "🗑️  移除 FundQuant 定时任务..."
    crontab -l | grep -v "fundquant" | crontab - 2>/dev/null
    echo "✅ 已移除"
    exit 0
fi

# 验证时间格式
if ! [[ "$SCHEDULE_TIME" =~ ^[0-9]{2}:[0-9]{2}$ ]]; then
    echo "❌ 时间格式错误，请使用 HH:MM 格式"
    exit 1
fi

HOUR=$(echo $SCHEDULE_TIME | cut -d: -f1)
MINUTE=$(echo $SCHEDULE_TIME | cut -d: -f2)

# 构建 crontab 行
CRON_ENTRY="# FundQuant 基金日报 - 每天 $SCHEDULE_TIME
${MINUTE} ${HOUR} * * 1-5 cd $PROJECT_DIR && python3 $CRON_SCRIPT --cron >> $LOG_FILE 2>&1
"

echo "📅 安装 FundQuant 定时任务..."
echo "   时间: 每周一到周五 $SCHEDULE_TIME"
echo "   脚本: $CRON_SCRIPT"
echo "   日志: $LOG_FILE"
echo ""

# 移除旧任务，添加新任务
(crontab -l 2>/dev/null | grep -v "fundquant" ; echo "$CRON_ENTRY") | crontab -

# 显示结果
echo "✅ 定时任务已安装!"
echo ""
echo "当前 crontab:"
crontab -l | grep fundquant || echo "  (无)"
