import json
import time
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

# 全局变量
EVENTS_DIR = './events'

# 邮件服务器配置
smtp_server = 'smtp.163.com'
smtp_port = 465 
# smtp_user从key文件中读取

def getSmtpCredentials():
    """获取SMTP用户名和密码"""
    try:
        with open('key', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) >= 2:
                # 如果key文件有至少两行，第一行是用户名，第二行是密码
                return lines[0].strip(), lines[1].strip()
            else:
                print("key文件格式不正确，需要包含用户名和密码")
                return None, None
    except Exception as e:
        print(f"无法读取SMTP凭据: {e}")
        return None, None

def generateHtml(data, date):
    """生成HTML邮件内容"""
    html_content = f"""
    <html>
    <head>
        <style>
            :root {{
                --primary-color: #2c3e50;
                --secondary-color: #3498db;
                --text-color: #333;
                --light-text: #777;
                --border-color: #eaeaea;
                --background-color: #f9f9f9;
                --card-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: var(--text-color);
                background-color: var(--background-color);
                margin: 0;
                padding: 20px;
                max-width: 1200px;
                margin: 0 auto;
            }}
            h1 {{
                color: var(--primary-color);
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 15px;
                border-bottom: 1px solid var(--border-color);
            }}
            .notification-container {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                gap: 20px;
            }}
            .notification {{
                background: white;
                border-radius: 8px;
                padding: 20px;
                box-shadow: var(--card-shadow);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }}
            .notification:hover {{
                transform: translateY(-3px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }}
            .title {{
                font-size: 17px;
                font-weight: 600;
                margin-bottom: 8px;
            }}
            .title a {{
                color: var(--primary-color);
                text-decoration: none;
                transition: color 0.2s ease;
            }}
            .title a:hover {{
                color: var(--secondary-color);
                text-decoration: underline;
            }}
            .unit {{
                font-size: 14px;
                color: var(--light-text);
                margin-bottom: 10px;
                padding-bottom: 10px;
                border-bottom: 1px dashed var(--border-color);
            }}
            .summary {{
                font-size: 14px;
                line-height: 1.5;
            }}
            @media (max-width: 768px) {{
                .notification-container {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <h1>{date} 通知汇总</h1>
        <div class="notification-container">
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
        </div>
    </body>
    </html>
    """
    return html_content

def sendEmail(file_path, recipient_email):
    """发送邮件到指定收件人"""
    try:
        date = os.path.basename(file_path).replace('.json', '')
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        if not data:
            print(f"文件 {file_path} 不包含数据，跳过为 {recipient_email} 发送邮件")
            return False
            
        html_content = generateHtml(data, date)
        smtp_user, smtp_password = getSmtpCredentials()
        if not smtp_user or not smtp_password:
            print(f"无法获取SMTP凭据，为 {recipient_email} 发送邮件失败")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipient_email
        msg['Subject'] = f'{date} OA通知汇总'
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipient_email, msg.as_string())
        server.quit()
        
        print(f"成功发送 {date} 的邮件通知给 {recipient_email}")
        return True
    except Exception as e:
        print(f"为 {recipient_email} 发送邮件失败 ({file_path}): {e}")
        return False

def getEmailList():
    """从List.txt读取邮箱地址列表"""
    try:
        if not os.path.exists('List.txt'):
            print("List.txt文件不存在，请创建该文件并添加邮箱地址（每行一个）")
            return []
            
        with open('List.txt', 'r', encoding='utf-8') as f:
            emails = [line.strip() for line in f if line.strip() and '@' in line]
            
        if not emails:
            print("List.txt文件中没有找到有效的邮箱地址")
            return []
            
        print(f"从List.txt中读取到{len(emails)}个邮箱地址")
        return emails
    except Exception as e:
        print(f"读取邮箱列表时出错: {e}")
        return []

def processNewFiles():
    """处理events目录中的前一天的JSON文件并发送邮件"""
    try:
        if not os.path.exists(EVENTS_DIR):
            print(f"目录 {EVENTS_DIR} 不存在，请确保该目录已创建")
            return
            
        # 获取所有JSON文件
        json_files = [os.path.join(EVENTS_DIR, f) for f in os.listdir(EVENTS_DIR) if f.endswith('.json')]
        
        if not json_files:
            print(f"在 {EVENTS_DIR} 目录中没有找到JSON文件")
            return
        
        # 获取前一天的日期
        import datetime
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        yesterday_file = os.path.join(EVENTS_DIR, f"{yesterday_str}.json")
        
        # 检查前一天的文件是否存在
        if os.path.exists(yesterday_file):
            print(f"找到前一天({yesterday_str})的JSON文件: {yesterday_file}")
            target_file = yesterday_file
        else:
            print(f"未找到前一天({yesterday_str})的JSON文件，将使用最新文件")
            # 按修改时间排序，最新的文件排在前面
            json_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            target_file = json_files[0]
            print(f"使用最新的JSON文件: {target_file}")
        
        # 获取邮箱列表
        email_list = getEmailList()
        if not email_list:
            return
            
        # 发送邮件
        success_count = 0
        for email in email_list:
            if sendEmail(target_file, email):
                success_count += 1
                
        print(f"邮件发送完成，成功: {success_count}/{len(email_list)}")
        
    except Exception as e:
        print(f"处理文件时出错: {e}")

if __name__ == '__main__':
    print("开始处理OA通知并发送邮件...")
    processNewFiles()
    print("处理完成")