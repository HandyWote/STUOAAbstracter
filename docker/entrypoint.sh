#!/bin/sh
set -euo pipefail

cron_file=/etc/cron.d/oap

cp /app/docker/cronjob "$cron_file"
chmod 0644 "$cron_file"

touch /var/log/oap.log
touch /var/log/cron.log

echo "Cron service启动，计划任务:"
cat "$cron_file"

if [ "${RUN_ON_START:-0}" = "1" ]; then
    default_date="$(date +%Y-%m-%d)"
    override_date="${RUN_ON_START_DATE:-$default_date}"
    echo "检测到 RUN_ON_START=1，立即执行一次任务 (TARGET_DATE_OVERRIDE=$override_date)"
    set +e
    TARGET_DATE_OVERRIDE="$override_date" /app/docker/run_oap.sh
    initial_status=$?
    set -e
    echo "预运行完成，状态码: $initial_status"
fi

exec cron -f -L 15
