"""Entrypoint that runs the OA spider and sends the digest email."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from spider.OAP import OA  # noqa: E402
from sender.Sender import Sender  # noqa: E402


def _normalize_target_date(raw: str | None) -> str:
    if raw is None:
        target = datetime.now() - timedelta(days=1)
        return target.strftime("%Y-%m-%d")

    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError("日期格式必须为 YYYY-MM-DD") from exc

    return parsed.strftime("%Y-%m-%d")


def main(target_date: str | None = None) -> None:
    date_str = _normalize_target_date(target_date)
    print(f"计划处理 {date_str} 的OA通知")

    spider = OA(target_date=date_str)
    spider.run()

    events_file = spider.events_dir / f"{date_str}.json"
    if not events_file.exists():
        print(f"未生成 {events_file}，跳过发送邮件")
        return

    sender = Sender(target_date=date_str)
    sender.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抓取OA通知并发送邮件")
    parser.add_argument("--date", help="指定目标日期，默认使用昨天 (YYYY-MM-DD)")
    args = parser.parse_args()

    try:
        main(target_date=args.date)
    except ValueError as exc:
        print(exc)
