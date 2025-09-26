#!/bin/sh
set -euo pipefail

cd /app

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

echo "[$(timestamp)] 开始执行 OA 抓取与邮件发送" >> /var/log/oap.log

if [ -n "${TARGET_DATE_OVERRIDE:-}" ]; then
    echo "[$(timestamp)] 检测到 TARGET_DATE_OVERRIDE=${TARGET_DATE_OVERRIDE}" >> /var/log/oap.log
    python main.py --date "$TARGET_DATE_OVERRIDE" >> /var/log/oap.log 2>&1
else
    python main.py >> /var/log/oap.log 2>&1
fi

status=$?
echo "[$(timestamp)] 任务结束，状态码: $status" >> /var/log/oap.log

exit "$status"
