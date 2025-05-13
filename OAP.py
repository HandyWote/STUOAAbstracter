import json
import re
import time
from json import dumps
from pprint import pprint

import requests
from bs4 import BeautifulSoup
class OA:
    def __init__(self):
        self.events = []
        self.now_time = self.getTime()
        self.data = {
            "pageindex": '1',
            "pagesize": "50",
            "fwdw": "-1"
        }
        oaurl = 'http://oa.stu.edu.cn/csweb/list.jsp'
        r_text = self.geturl(oaurl)
        self.events = self.getEvents(r_text, self.now_time)
        self.getAbstract(self.events)

    def getTime(self):
        tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst = time.localtime()
        now_time = f"{tm_year:0>4d}-{tm_mon:0>2d}-{tm_mday:0>2d}"
        return now_time

    def geturl(self, url):
        r = requests.post(url, data=self.data)
        r_text = r.text
        return r_text

    def getEvents(self, html_text, now_time):
        """
        从HTML文本中提取<tbody>内容并转换为结构化格式

        参数:
            html_text (str): 包含HTML的文本
            now_time (str): 当天时间

        返回:
            pandas.DataFrame: 包含提取数据的表格
        """
        soup = BeautifulSoup(html_text, 'html.parser')
        tbody = soup.find('tbody')
        if not tbody:
            return None
        rows = tbody.find_all('tr', class_='datalight')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 3:
                title_link = cells[0].find('a')
                title = title_link.get('title', '').strip() if title_link else ''
                href = title_link.get('href', '') if title_link else ''
                department = cells[1].get_text(strip=True)
                date = cells[2].get_text(strip=True)
                if date != now_time:
                    break
                self.events.append({
                    '标题': title,
                    '链接': 'http://oa.stu.edu.cn/' + href,
                    '发布单位': department,
                    '发布日期': date
                })
        return self.events

    def remove_html_tags(self, text):
        text = re.sub(r'^.*?}', '', text, flags=re.DOTALL)
        clean_text = re.sub(r'<.*?>', '', text)
        clean_text = re.sub(r'\s+', '', clean_text)
        return clean_text

    def getAbstract(self, events):
        for i, event in enumerate(events):
            link = event['链接']
            html_text = self.geturl(link)
            soup = BeautifulSoup(html_text, 'html.parser')
            tbody = soup.find('tbody')
            tbody = tbody.find('tbody')
            td = tbody.find('td')
            article = self.remove_html_tags(str(td))
            abstract = self.postAi(article)
            self.events[i]['摘要'] = abstract

    def postAi(self, words):
        header = {
            "Authorization": 'Bearer 6439f3eb9be940cb836e23773388df88.fUMSa6LsAkZyIrrC',
            "Content-Type": "application/json"
        }
        data = {
            "model": 'glm-z1-flash',
            "messages": [{"role": "system", "content": '''你是一个顶级的秘书，现在给你一篇文章，请你在不改变原意的情况下概括出这篇文章的的摘要，简介明了的说明。格式要求：最后结果要放到[]里，如[摘要]'''},{"role": "user", "content": words}],
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        r = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", json=data, headers=header)
        r = r.json()
        content = r['choices'][-1]['message']['content']
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        content = re.sub(r'^.*?【', '', content, flags=re.DOTALL).strip()
        content = re.sub(r'\(.*?\)', '', content, flags=re.DOTALL).strip()
        return content

if __name__ == '__main__':
    oa = OA()