#!/bin/sh
set -euo pipefail

cron_file=/etc/cron.d/oap

cp /app/docker/cronjob "$cron_file"
chmod 0644 "$cron_file"
crontab "$cron_file"

touch /var/log/oap.log
touch /var/log/cron.log

echo "Cron service启动，计划任务:"
crontab -l

exec cron -f -L 15
