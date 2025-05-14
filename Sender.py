import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib


# 加载JSON文件内容
file_path = './events/2025-05-14.json'
with open(file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

# 将JSON数据转换为HTML格式
html_content = """
<html>
<head>
    <style>
        :root {
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --text-color: #333;
            --light-text: #777;
            --border-color: #eaeaea;
            --background-color: #f9f9f9;
            --card-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--background-color);
            margin: 0;
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        h1 {
            color: var(--primary-color);
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .notification-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }
        
        .notification {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: var(--card-shadow);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .notification:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        .title {
            font-size: 17px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .title a {
            color: var(--primary-color);
            text-decoration: none;
            transition: color 0.2s ease;
        }
        
        .title a:hover {
            color: var(--secondary-color);
            text-decoration: underline;
        }
        
        .unit {
            font-size: 14px;
            color: var(--light-text);
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px dashed var(--border-color);
        }
        
        .summary {
            font-size: 14px;
            line-height: 1.5;
        }
        
        @media (max-width: 768px) {
            .notification-container {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <h1>2025-05-14 通知汇总</h1>
"""

for item in data:
    html_content += f"""
    <div class="notification">
        <div class="title"><a href="{item['链接']}">{item['标题']}</a></div>
        <div class="unit">{item['发布单位']}</div>
        <div class="summary">{item['摘要']}</div>
    </div>
    """

html_content += """
</body>
</html>
"""


### 第二步：发送邮件

# 邮件服务器配置
smtp_server = 'smtp.163.com'  # 替换为你的SMTP服务器地址
smtp_port = 465  # SMTP端口，通常为465
smtp_user = 'handywote@163.com'  # 从环境变量中获取邮箱地址
smtp_password = open('TAa2gsKe9w5XkkcR', 'r', encoding='utf-8').readline().strip()# 从环境变量中获取邮箱密码
to_address = '24syfeng@stu.edu.cn'
# 邮件内容
msg = MIMEMultipart()
msg['From'] = smtp_user
msg['To'] = to_address
msg['Subject'] = '2025-05-14 OA通知汇总'

# 添加HTML内容
msg.attach(MIMEText(html_content, 'html', 'utf-8'))

# 发送邮件
try:
    server = smtplib.SMTP_SSL(smtp_server, smtp_port)  # 使用SSL加密
    server.login(smtp_user, smtp_password)
    server.sendmail(smtp_user, to_address, msg.as_string())
    server.quit()
    print("邮件发送成功！")
except Exception as e:
    print(f"邮件发送失败：{e}")