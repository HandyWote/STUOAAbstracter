import json
import re
import time
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

    def __init__(self) -> None:
        self.config = Config()
        self.config.ensure_directories()
        self.events_dir: Path = self.config.events_dir
        self.today = time.strftime("%Y-%m-%d", time.localtime())
        self.payload = {"pageindex": "1", "pagesize": "50", "fwdw": "-1"}
        self.events: list[dict[str, str]] = []

    def run(self) -> None:
        page = self._post(self.BASE_URL, self.payload)
        if not page:
            print("获取OA页面失败，无法继续处理")
            return

        events = self._parse_events(page)
        if not events:
            print("今日没有需要记录的通知")
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
            if date != self.today:
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

    def _fill_summaries(self) -> None:
        for event in self.events:
            detail_html = self._post(event["链接"], self.payload)
            if not detail_html:
                event["摘要"] = "[获取摘要失败]"
                continue

            article = self._clean_html(detail_html)
            summary = self._call_ai(article)
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
                        "你是一个顶级的秘书，现在给你一篇文章，请你在不改变原意的情况下"
                        "概括出这篇文章的的摘要，简介明了的说明。格式要求：最后结果要放到[]里，如[摘要]"
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

        output_file = self.events_dir / f"{self.today}.json"
        try:
            with output_file.open("w", encoding="utf-8") as handle:
                json.dump(self.events, handle, ensure_ascii=False, indent=4)
            print(f"成功保存{len(self.events)}条事件到文件: {output_file}")
        except OSError as exc:
            print(f"保存文件时发生错误: {exc}")


if __name__ == "__main__":
    OA().run()
