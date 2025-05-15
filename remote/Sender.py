import json
import time
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from flask import Flask, jsonify, request
import threading
import logging
import sqlite3
from datetime import datetime, timedelta

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
DATABASE_FILE = 'subscriptions.db'

# 邮件服务器配置
smtp_server = 'smtp.163.com'
smtp_port = 465 
smtp_user = 'handywote@163.com'
# to_address = '24syfeng@stu.edu.cn' # 不再使用单一收件人，改为从数据库读取

# --- 数据库操作 --- 
def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # 订阅用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            subscription_date DATETIME NOT NULL,
            expiry_date DATETIME NOT NULL,
            status TEXT CHECK(status IN ('active', 'expired', 'cancelled')) DEFAULT 'active',
            payment_method TEXT,
            last_payment_date DATETIME
        )
    ''')
    # 邮件发送日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            recipient_email TEXT NOT NULL,
            sent_time DATETIME NOT NULL,
            status TEXT CHECK(status IN ('success', 'failed')) DEFAULT 'success',
            error_message TEXT
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("数据库初始化完成或已存在.")

def add_subscriber(email, subscription_duration_days=30, payment_method='default'):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        subscription_date = datetime.now()
        expiry_date = subscription_date + timedelta(days=subscription_duration_days)
        cursor.execute('''
            INSERT INTO subscribers (email, subscription_date, expiry_date, status, payment_method, last_payment_date)
            VALUES (?, ?, ?, 'active', ?, ?)
            ON CONFLICT(email) DO UPDATE SET
            subscription_date = excluded.subscription_date,
            expiry_date = excluded.expiry_date,
            status = 'active',
            payment_method = excluded.payment_method,
            last_payment_date = excluded.last_payment_date;
        ''', (email, subscription_date, expiry_date, payment_method, subscription_date))
        conn.commit()
        logger.info(f"订阅用户 {email} 添加/更新成功，有效期至 {expiry_date.strftime('%Y-%m-%d')}.")
        return True
    except sqlite3.Error as e:
        logger.error(f"添加/更新订阅用户 {email} 失败: {e}")
        return False
    finally:
        conn.close()

def get_active_subscribers():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT email FROM subscribers WHERE status = 'active' AND expiry_date > ?", (datetime.now(),))
        subscribers = [row['email'] for row in cursor.fetchall()]
        return subscribers
    except sqlite3.Error as e:
        logger.error(f"获取活跃订阅用户失败: {e}")
        return []
    finally:
        conn.close()

def log_email_send(file_path, recipient_email, status='success', error_message=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO email_logs (file_path, recipient_email, sent_time, status, error_message)
            VALUES (?, ?, ?, ?, ?)
        ''', (file_path, recipient_email, datetime.now(), status, error_message))
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"记录邮件发送日志失败 ({recipient_email}, {file_path}): {e}")
    finally:
        conn.close()

def cancel_subscriber(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE subscribers SET status = 'cancelled' WHERE email = ?", (email,))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"用户 {email} 已取消订阅.")
            return True
        else:
            logger.warning(f"尝试取消订阅失败：未找到用户 {email}.")
            return False
    except sqlite3.Error as e:
        logger.error(f"取消订阅用户 {email} 失败: {e}")
        return False
    finally:
        conn.close()

# --- 邮件功能 --- 
def getSmtpPassword():
    try:
        with open('key', 'r', encoding='utf-8') as f:
            return f.readline().strip()
    except Exception as e:
        logger.error(f"无法读取SMTP密码: {e}")
        return None

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

def sendEmail(file_path, recipient_email):
    try:
        date = os.path.basename(file_path).replace('.json', '')
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        if not data:
            logger.warning(f"文件 {file_path} 不包含数据，跳过为 {recipient_email} 发送邮件")
            log_email_send(file_path, recipient_email, status='failed', error_message='Empty JSON data')
            return False
            
        html_content = generateHtml(data, date)
        smtp_password = getSmtpPassword()
        if not smtp_password:
            logger.error(f"无法获取SMTP密码，为 {recipient_email} 发送邮件失败")
            log_email_send(file_path, recipient_email, status='failed', error_message='SMTP password not found')
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
        
        logger.info(f"成功发送 {date} 的邮件通知给 {recipient_email}")
        log_email_send(file_path, recipient_email, status='success')
        return True
    except Exception as e:
        logger.error(f"为 {recipient_email} 发送邮件失败 ({file_path}): {e}")
        log_email_send(file_path, recipient_email, status='failed', error_message=str(e))
        return False

# --- 文件监控与处理 --- 
def checkNewFiles():
    try:
        if not os.path.exists(EVENTS_DIR):
            logger.warning(f"目录 {EVENTS_DIR} 不存在")
            return
            
        json_files = [os.path.join(EVENTS_DIR, f) for f in os.listdir(EVENTS_DIR) 
                     if f.endswith('.json') and os.path.join(EVENTS_DIR, f) not in processed_files]
        
        if not json_files:
            return
            
        logger.info(f"发现 {len(json_files)} 个新的JSON文件待处理")
        active_subscribers = get_active_subscribers()
        if not active_subscribers:
            logger.warning("没有活跃的订阅用户，跳过邮件发送")
            # 仍然将文件标记为已处理，避免重复检查，但没有实际发送
            for file_path in json_files:
                 processed_files.add(file_path)
                 logger.info(f"文件 {file_path} 已标记为处理（无活跃订阅者）")
            return

        logger.info(f"将为 {len(active_subscribers)} 个活跃订阅用户发送邮件")
        
        for file_path in json_files:
            all_sent_successfully_for_this_file = True
            for subscriber_email in active_subscribers:
                if not sendEmail(file_path, subscriber_email):
                    all_sent_successfully_for_this_file = False # 记录是否有任何一个用户发送失败
            
            # 只有当该文件对所有活跃用户都尝试发送后（无论成功与否），才标记为已处理
            processed_files.add(file_path)
            logger.info(f"文件 {file_path} 已处理完成 (尝试发送给所有活跃订阅者)")

    except Exception as e:
        logger.error(f"检查新文件时出错: {e}")

def fileMonitorThread():
    while True:
        checkNewFiles()
        time.sleep(3600) 

# --- API路由 --- 
@app.route('/api/subscribe', methods=['POST'])
def api_subscribe():
    data = request.json
    if not data or 'email' not in data:
        return jsonify({"status": "error", "message": "缺少email参数"}), 400
    
    email = data['email']
    # 支付验证逻辑 (用户需自行实现)
    # payment_token = data.get('payment_token')
    # if not verify_payment(payment_token): # verify_payment 是一个假设的函数
    #     return jsonify({"status": "error", "message": "支付验证失败"}), 402

    duration_days = data.get('duration_days', 365) # 默认订阅30天
    payment_method = data.get('payment_method', 'default_api_method')

    if add_subscriber(email, duration_days, payment_method):
        return jsonify({"status": "success", "message": f"用户 {email} 订阅成功，有效期 {duration_days} 天"})
    else:
        return jsonify({"status": "error", "message": f"用户 {email} 订阅失败"}), 500

@app.route('/api/unsubscribe', methods=['POST'])
def api_unsubscribe():
    data = request.json
    if not data or 'email' not in data:
        return jsonify({"status": "error", "message": "缺少email参数"}), 400
    
    email = data['email']
    if cancel_subscriber(email):
        return jsonify({"status": "success", "message": f"用户 {email} 已取消订阅"})
    else:
        return jsonify({"status": "error", "message": f"取消订阅用户 {email} 失败或用户不存在"}), 500

@app.route('/api/check-and-send', methods=['GET'])
def apiCheckAndSend():
    checkNewFiles()
    return jsonify({"status": "success", "message": "手动检查和发送邮件任务已触发"})

# 原有的 /api/send-email 端点，现在改为发送给特定用户（如果需要保留的话）
# 或者可以移除，因为 checkNewFiles 会处理所有订阅者
# 为了演示，我们修改它为给特定用户发送特定文件，主要用于测试
@app.route('/api/send-email-to-user', methods=['POST'])
def apiSendEmailToUser():
    data = request.json
    if not data or 'file_path' not in data or 'email' not in data:
        return jsonify({"status": "error", "message": "缺少file_path或email参数"}), 400
        
    file_path = data['file_path']
    recipient_email = data['email']

    if not os.path.exists(file_path):
        return jsonify({"status": "error", "message": f"文件 {file_path} 不存在"}), 404
        
    # 检查用户是否存在且活跃 (可选，但推荐)
    # conn = get_db_connection()
    # cursor = conn.cursor()
    # cursor.execute("SELECT 1 FROM subscribers WHERE email = ? AND status = 'active' AND expiry_date > ?", (recipient_email, datetime.now()))
    # if not cursor.fetchone():
    #     conn.close()
    #     return jsonify({"status": "error", "message": f"用户 {recipient_email} 不是活跃订阅者"}), 403
    # conn.close()

    success = sendEmail(file_path, recipient_email)
    if success:
        # 注意：这个端点不应该影响 processed_files 的主逻辑
        return jsonify({"status": "success", "message": f"成功发送 {os.path.basename(file_path)} 的邮件给 {recipient_email}"})
    else:
        return jsonify({"status": "error", "message": "邮件发送失败"}), 500

@app.route('/api/status', methods=['GET'])
def apiStatus():
    conn = get_db_connection()
    cursor = conn.cursor()
    total_subscribers = 0
    active_subscribers_count = 0
    try:
        cursor.execute("SELECT COUNT(*) as count FROM subscribers")
        total_subscribers = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM subscribers WHERE status = 'active' AND expiry_date > ?", (datetime.now(),))
        active_subscribers_count = cursor.fetchone()['count']
    except sqlite3.Error as e:
        logger.error(f"获取状态时查询数据库失败: {e}")
    finally:
        conn.close()

    return jsonify({
        "status": "running",
        "processed_files_count": len(processed_files),
        "events_dir": EVENTS_DIR,
        "database_file": DATABASE_FILE,
        "total_subscribers": total_subscribers,
        "active_subscribers": active_subscribers_count
    })

# 启动应用
if __name__ == '__main__':
    init_db() # 初始化数据库和表

    # 初始化已处理文件列表 (与之前逻辑相同)
    if os.path.exists(EVENTS_DIR):
        processed_files = set([os.path.join(EVENTS_DIR, f) for f in os.listdir(EVENTS_DIR) if f.endswith('.json')])
        logger.info(f"初始化时，事件目录中已有 {len(processed_files)} 个文件被认为是已处理过的")
    
    monitor_thread = threading.Thread(target=fileMonitorThread, daemon=True)
    monitor_thread.start()
    logger.info("文件监控线程已启动")
    
    app.run(host='0.0.0.0', port=5000, debug=False)