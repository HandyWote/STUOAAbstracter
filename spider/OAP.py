import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import requests
from bs4 import BeautifulSoup

from config.config import Config


class OA:
    BASE_URL = "http://oa.stu.edu.cn/login/Login.jsp?logintype=1"
    AI_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def __init__(self, target_date: str | None = None) -> None:
        self.config = Config()
        self.config.ensure_directories()
        self.events_dir: Path = self.config.events_dir
        self.target_date = self._normalize_date(target_date)
        self.payload = {"pageindex": "1", "pagesize": "50", "fwdw": "-1"}
        self.events: list[dict[str, str]] = []

    def run(self) -> None:
        print(f"开始抓取 {self.target_date} 的OA通知...")
        page = self._post(self.BASE_URL, self.payload)
        if not page:
            print("获取OA页面失败，无法继续处理")
            return

        events = self._parse_events(page)
        if not events:
            print(f"{self.target_date} 没有需要记录的通知")
            return

        self.events = events
        self._fill_summaries()
        self._save_events()

    def _post(self, url: str, data: dict[str, str] | None = None) -> str | None:
        try:
            response = requests.post(url, data=data, timeout=30)
            if response.status_code == 200:
                return response.text
            print(f"请求失败，状态码: {response.status_code}")
        except requests.RequestException as exc:
            print(f"请求 {url} 失败: {exc}")
        return None

    def _parse_events(self, html: str) -> list[dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        tbody = soup.find("tbody")
        if not tbody:
            return []

        result: list[dict[str, str]] = []
        for row in tbody.find_all("tr", class_="datalight"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            link = cells[0].find("a")
            if not link:
                continue

            date = cells[2].get_text(strip=True)
            if date > self.target_date:
                continue
            if date < self.target_date:
                break

            href = link.get("href", "").strip()
            if not href:
                continue

            result.append(
                {
                    "标题": link.get("title", "").strip() or link.get_text(strip=True),
                    "链接": f"http://oa.stu.edu.cn{href}",
                    "发布单位": cells[1].get_text(strip=True),
                    "发布日期": date,
                }
            )
        print(f"成功提取{len(result)}条事件")
        return result

    @staticmethod
    def _normalize_date(raw: str | None) -> str:
        if raw is None:
            return time.strftime("%Y-%m-%d", time.localtime())

        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            raise ValueError("日期格式必须为 YYYY-MM-DD") from None

        return parsed.strftime("%Y-%m-%d")

    def _fill_summaries(self) -> None:
        total = len(self.events)
        if total == 0:
            return

        print(f"开始生成摘要，共 {total} 条事件")
        for index, event in enumerate(self.events, start=1):
            title = event.get("标题", "[无标题]")
            print(f"[{index}/{total}] 拉取详情: {title}")

            detail_html = self._post(event["链接"], self.payload)
            if not detail_html:
                event["摘要"] = "[获取摘要失败]"
                print(f"[{index}/{total}] 详情获取失败，已标记占位摘要")
                continue

            article = self._clean_html(detail_html)
            summary = self._call_ai(article)
            if not summary:
                print(f"[{index}/{total}] 摘要生成失败，已使用占位文本")
            else:
                print(f"[{index}/{total}] 摘要生成完成")
            
            # 清理摘要中的 # 号和开头的空格
            if summary:
                summary = summary.lstrip('# ').lstrip()
            
            event["摘要"] = summary or "[摘要生成失败]"

    def _clean_html(self, text: str) -> str:
        text = re.sub(r"^.*?}", "", text, flags=re.DOTALL)
        text = re.sub(r"<.*?>", "", text)
        return re.sub(r"\s+", "", text)

    def _call_ai(self, content: str) -> str | None:
        headers = dict(self.config.ai_headers)
        if "Authorization" not in headers:
            print("AI API_KEY 未配置，跳过摘要生成")
            return "[AI 未配置]"

        payload = {
            "model": "glm-4.5-flash",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一个顶级新闻主编，现在给你一篇文章，请你在不改变原意的情况下"
                        "精准概括出这篇文章的的摘要，简洁明了的讲清楚事件。"
                    ),
                },
                {"role": "user", "content": content},
            ],
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        try:
            response = requests.post(self.AI_URL, json=payload, headers=headers, timeout=60)
            if response.status_code != 200:
                print(f"AI API返回错误状态码: {response.status_code}")
                return "[AI服务异常]"

            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                print("AI API返回格式异常: 没有choices字段")
                return "[AI返回格式异常]"

            content = choices[-1]["message"].get("content", "").strip()
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            content = re.sub(r"^.*?【", "", content, flags=re.DOTALL).strip()
            content = re.sub(r"\(.*?\)", "", content, flags=re.DOTALL).strip()

            return content
        except requests.exceptions.Timeout:
            print("AI API请求超时")
            return "[AI请求超时]"
        except requests.exceptions.ConnectionError:
            print("AI API连接错误")
            return "[AI连接失败]"
        except ValueError as exc:
            print(f"解析AI API返回的JSON时出错: {exc}")
            return "[AI返回解析失败]"
        except requests.RequestException as exc:
            print(f"调用AI API时发生错误: {exc}")
            return "[AI调用失败]"

    def _save_events(self) -> None:
        if not self.events:
            print("没有事件数据可保存")
            return

        output_file = self.events_dir / f"{self.target_date}.json"
        try:
            with output_file.open("w", encoding="utf-8") as handle:
                json.dump(self.events, handle, ensure_ascii=False, indent=4)
            print(f"成功保存{len(self.events)}条事件到文件: {output_file}")
        except OSError as exc:
            print(f"保存文件时发生错误: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抓取OA通知并生成指定日期的JSON文件")
    parser.add_argument("--date", help="目标日期，格式 YYYY-MM-DD，默认抓取当天")
    args = parser.parse_args()

    try:
        OA(target_date=args.date).run()
    except ValueError as exc:
        print(exc)
