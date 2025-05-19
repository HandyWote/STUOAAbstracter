import json
import re
import time
import requests
import os
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
        oaurl = 'http://oa.stu.edu.cn/login/Login.jsp?logintype=1'
        
        try:
            # 确保events目录存在
            if not os.path.exists('./events'):
                os.makedirs('./events')
                
            # 主要流程
            r_text = self.getUrl(oaurl)
            if r_text:
                self.getEvents(r_text, self.now_time)
                self.getAbstract()
                self.out()
            else:
                print("获取OA页面失败，无法继续处理")
        except Exception as e:
            print(f"初始化过程中发生错误: {str(e)}")
            # 即使发生错误，也尝试保存已获取的数据
            if self.events:
                self.out()


    def getTime(self):
        tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, tm_wday, tm_yday, tm_isdst = time.localtime()
        now_time = f"{tm_year:0>4d}-{tm_mon:0>2d}-{tm_mday:0>2d}"
        return now_time

    def getUrl(self, url):
        try:
            r = requests.post(url, data=self.data, timeout=30)
            if r.status_code == 200:
                return r.text
            else:
                print(f"请求URL: {url} 返回非200状态码: {r.status_code}")
                return None
        except requests.exceptions.Timeout:
            print(f"请求URL: {url} 超时")
            return None
        except requests.exceptions.ConnectionError:
            print(f"请求URL: {url} 连接错误")
            return None
        except Exception as e:
            print(f"请求URL: {url} 发生错误: {str(e)}")
            return None

    def getEvents(self, html_text, now_time):
        """
        从HTML文本中提取<tbody>内容并转换为结构化格式

        参数:
            html_text (str): 包含HTML的文本
            now_time (str): 当天时间
        """
        if not html_text:
            print("HTML文本为空，无法提取事件")
            return None
            
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            tbody = soup.find('tbody')
            if not tbody:
                print("未找到tbody元素")
                return None
                
            rows = tbody.find_all('tr', class_='datalight')
            if not rows:
                print("未找到数据行")
                return None
                
            event_count = 0
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        title_link = cells[0].find('a')
                        title = title_link.get('title', '').strip() if title_link else ''
                        href = title_link.get('href', '') if title_link else ''
                        department = cells[1].get_text(strip=True)
                        date = cells[2].get_text(strip=True)
                        
                        if date != now_time:
                            break
                            
                        if title and href:
                            self.events.append({
                                '标题': title,
                                '链接': 'http://oa.stu.edu.cn' + href,
                                '发布单位': department,
                                '发布日期': date
                            })
                            event_count += 1
                        else:
                            print(f"跳过无效事件: 标题或链接为空")
                except Exception as e:
                    print(f"处理数据行时发生错误: {str(e)}")
                    continue  # 继续处理下一行
                    
            print(f"成功提取{event_count}条事件")
        except Exception as e:
            print(f"提取事件时发生错误: {str(e)}")
            return None

    def getAbstract(self):
        for i, event in enumerate(self.events):
            try:
                link = event['链接']
                print(f"正在获取摘要: {event['标题']}")
                
                html_text = self.getUrl(link)
                if not html_text:
                    print(f"获取链接内容失败: {link}")
                    self.events[i]['摘要'] = "[获取摘要失败]"  # 设置默认摘要
                    continue
                    
                try:
                    soup = BeautifulSoup(html_text, 'html.parser')
                    tbody = soup.find('tbody')
                    if not tbody:
                        print(f"未找到tbody元素: {link}")
                        self.events[i]['摘要'] = "[解析内容失败]"  # 设置默认摘要
                        continue
                        
                    tbody = tbody.find('tbody')
                    if not tbody:
                        print(f"未找到嵌套tbody元素: {link}")
                        self.events[i]['摘要'] = "[解析内容失败]"  # 设置默认摘要
                        continue
                        
                    td = tbody.find('td')
                    if not td:
                        print(f"未找到td元素: {link}")
                        self.events[i]['摘要'] = "[解析内容失败]"  # 设置默认摘要
                        continue
                        
                    article = self.removeHtmlTags(str(td))
                    abstract = self.postAi(article)
                    
                    if abstract:
                        self.events[i]['摘要'] = abstract
                    else:
                        self.events[i]['摘要'] = "[摘要生成失败]"  # 设置默认摘要
                        
                except Exception as e:
                    print(f"解析HTML内容时发生错误: {str(e)}")
                    self.events[i]['摘要'] = "[解析内容出错]"  # 设置默认摘要
                    
            except Exception as e:
                print(f"获取摘要过程中发生错误: {str(e)}")
                if i < len(self.events):  # 确保索引有效
                    self.events[i]['摘要'] = "[处理出错]"  # 设置默认摘要

    def removeHtmlTags(self, text):
        text = re.sub(r'^.*?}', '', text, flags=re.DOTALL)
        clean_text = re.sub(r'<.*?>', '', text)
        clean_text = re.sub(r'\s+', '', clean_text)
        return clean_text

    def postAi(self, words):
        if not words or len(words) < 10:  # 检查文本是否太短
            print("文章内容太短，无法生成摘要")
            return "[文章内容不足]"  # 返回默认摘要
            
        try:
            header = {
                "Authorization": 'Bearer 6439f3eb9be940cb836e23773388df88.fUMSa6LsAkZyIrrC',
                "Content-Type": "application/json"
            }
            data = {
                "model": 'glm-z1-flash',
                "messages": [{"role": "system", "content": '''你是一个顶级的秘书，现在给你一篇文章，请你在不改变原意的情况下概括出这篇文章的的摘要，简介明了的说明。格式要求：最后结果要放到[]里，如[摘要]'''},
                             {"role": "user", "content": words}],
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            # 设置超时，防止请求卡住
            r = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", 
                             json=data, headers=header, timeout=60)
            
            if r.status_code != 200:
                print(f"AI API返回错误状态码: {r.status_code}")
                return "[AI服务异常]"  # 返回默认摘要
                
            try:
                r_json = r.json()
                if 'choices' not in r_json or not r_json['choices']:
                    print("AI API返回格式异常: 没有choices字段")
                    return "[AI返回格式异常]"  # 返回默认摘要
                    
                content = r_json['choices'][-1]['message']['content']
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                content = re.sub(r'^.*?【', '', content, flags=re.DOTALL).strip()
                content = re.sub(r'\(.*?\)', '', content, flags=re.DOTALL).strip()
                
                # 确保摘要有内容
                if not content or len(content) < 5:  # 检查摘要是否太短
                    print("生成的摘要内容太短")
                    return "[摘要生成失败]"  # 返回默认摘要
                    
                return content
            except ValueError as e:
                print(f"解析AI API返回的JSON时出错: {str(e)}")
                return "[AI返回解析失败]"  # 返回默认摘要
                
        except requests.exceptions.Timeout:
            print("AI API请求超时")
            return "[AI请求超时]"  # 返回默认摘要
        except requests.exceptions.ConnectionError:
            print("AI API连接错误")
            return "[AI连接失败]"  # 返回默认摘要
        except Exception as e:
            print(f"调用AI API时发生错误: {str(e)}")
            return "[AI调用失败]"  # 返回默认摘要

    def out(self):
        if not self.events:
            print("没有事件数据可保存")
            return
            
        try:
            # 确保目录存在
            os.makedirs('./events', exist_ok=True)
            
            output_file = f'./events/{self.now_time}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.events, f, ensure_ascii=False, indent=4)
                
            print(f"成功保存{len(self.events)}条事件到文件: {output_file}")
            
            # 尝试上传文件到服务器
            self.uploadToServer(output_file)
        except IOError as e:
            print(f"保存文件时发生IO错误: {str(e)}")
        except Exception as e:
            print(f"保存文件时发生错误: {str(e)}")
            
    def uploadToServer(self, file_path):
        """
        将JSON文件上传到服务器
        
        参数:
            file_path (str): JSON文件的路径
        """
        try:
            print(f"开始上传文件到服务器: {file_path}")
            
            # TODO: 实现服务器连接和文件上传逻辑
            # 服务器连接信息
            server_url = "https://oap.handywote.top/api/upload"  # 服务器URL，待填写
            username = "handy"    # 用户名，待填写
            password = "H-yh520888"    # 密码，待填写
            
            # 上传逻辑示例
            if not os.path.exists(file_path):
                print(f"文件不存在，无法上传: {file_path}")
                return False
                
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(server_url, files=files, auth=(username, password))
                if response.status_code == 200:
                    print(f"文件上传成功: {file_path}")
                    return True
                else:
                    print(f"文件上传失败，状态码: {response.status_code}")
                    return False
            
            
        except Exception as e:
            print(f"上传文件时发生错误: {str(e)}")
            return False

if __name__ == '__main__':
    oa = OA()