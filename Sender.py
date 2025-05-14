import json
import time
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from flask import Flask, jsonify, request
import threading
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('EmailSender')

app = Flask(__name__)

# 全局变量
processed_files = set()
EVENTS_DIR = './events'

# 邮件服务器配置
smtp_server = 'smtp.163.com'
smtp_port = 465 
smtp_user = 'handywote@163.com'
to_address = '24syfeng@stu.edu.cn'

# 读取密码
def getSmtpPassword():
    try:
        with open('key', 'r', encoding='utf-8') as f:
            return f.readline().strip()
    except Exception as e:
        logger.error(f"无法读取SMTP密码: {e}")
        return None

# 生成HTML内容
def generateHtml(data, date):
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

# 发送邮件函数
def sendEmail(file_path):
    try:
        # 提取日期
        date = os.path.basename(file_path).replace('.json', '')
        
        # 加载JSON文件内容
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        if not data:
            logger.warning(f"文件 {file_path} 不包含数据，跳过发送邮件")
            return False
            
        # 生成HTML内容
        html_content = generateHtml(data, date)
        
        # 获取SMTP密码
        smtp_password = getSmtpPassword()
        if not smtp_password:
            logger.error("无法获取SMTP密码，邮件发送失败")
            return False
        
        # 邮件内容
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_address
        msg['Subject'] = f'{date} OA通知汇总'

        # 添加HTML内容
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        # 发送邮件
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)  # 使用SSL加密
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_address, msg.as_string())
        server.quit()
        
        logger.info(f"成功发送 {date} 的邮件通知")
        return True
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        return False

# 检查新文件并发送邮件
def checkNewFiles():
    try:
        if not os.path.exists(EVENTS_DIR):
            logger.warning(f"目录 {EVENTS_DIR} 不存在")
            return
            
        # 获取所有JSON文件
        json_files = [os.path.join(EVENTS_DIR, f) for f in os.listdir(EVENTS_DIR) 
                     if f.endswith('.json') and os.path.join(EVENTS_DIR, f) not in processed_files]
        
        if not json_files:
            return
            
        logger.info(f"发现 {len(json_files)} 个新的JSON文件")
        
        # 处理每个新文件
        for file_path in json_files:
            if sendEmail(file_path):
                processed_files.add(file_path)
                logger.info(f"已处理文件: {file_path}")
    except Exception as e:
        logger.error(f"检查新文件时出错: {e}")

# 定时检查新文件的线程函数
def fileMonitorThread():
    while True:
        checkNewFiles()
        time.sleep(3600) 

# API路由
@app.route('/api/check-and-send', methods=['GET'])
def apiCheckAndSend():
    checkNewFiles()
    return jsonify({"status": "success", "message": "检查完成"})

@app.route('/api/send-email', methods=['POST'])
def apiSendEmail():
    data = request.json
    if not data or 'file_path' not in data:
        return jsonify({"status": "error", "message": "缺少file_path参数"}), 400
        
    file_path = data['file_path']
    if not os.path.exists(file_path):
        return jsonify({"status": "error", "message": f"文件 {file_path} 不存在"}), 404
        
    success = sendEmail(file_path)
    if success:
        processed_files.add(file_path)
        return jsonify({"status": "success", "message": f"成功发送 {file_path} 的邮件"})
    else:
        return jsonify({"status": "error", "message": "邮件发送失败"}), 500

@app.route('/api/status', methods=['GET'])
def apiStatus():
    return jsonify({
        "status": "running",
        "processed_files": list(processed_files),
        "events_dir": EVENTS_DIR
    })

# 启动应用
if __name__ == '__main__':
    # 初始化已处理文件列表
    if os.path.exists(EVENTS_DIR):
        processed_files = set([os.path.join(EVENTS_DIR, f) for f in os.listdir(EVENTS_DIR) if f.endswith('.json')])
        logger.info(f"初始化时已有 {len(processed_files)} 个处理过的文件")
    
    # 启动文件监控线程
    monitor_thread = threading.Thread(target=fileMonitorThread, daemon=True)
    monitor_thread.start()
    logger.info("文件监控线程已启动")
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=False)