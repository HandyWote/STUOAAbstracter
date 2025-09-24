import datetime
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from config.config import Config


class Sender:
    """Send the most recent OA announcement digest to configured recipients."""

    def __init__(self) -> None:
        self.config = Config()
        self.events_dir = self.config.events_dir
        self._ensure_runtime_dirs()

    def run(self) -> None:
        print("开始处理OA通知并发送邮件...")
        self._process_new_files()
        print("处理完成")

    def _ensure_runtime_dirs(self) -> None:
        self.config.ensure_directories()

    def _get_smtp_credentials(self) -> tuple[str | None, str | None]:
        smtp_user = self.config.smtp_user
        smtp_password = self.config.smtp_password
        if not smtp_user or not smtp_password:
            print("未在配置中找到SMTP用户名或密码，请检查env文件或环境变量")
            return None, None
        return smtp_user, smtp_password

    @staticmethod
    def _generate_html(data, date: str) -> str:
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

    def _send_email(self, file_path: Path, recipient_email: str) -> bool:
        try:
            date = file_path.stem
            with file_path.open('r', encoding='utf-8') as file:
                data = json.load(file)

            if not data:
                print(f"文件 {file_path} 不包含数据，跳过为 {recipient_email} 发送邮件")
                return False

            html_content = self._generate_html(data, date)
            smtp_user, smtp_password = self._get_smtp_credentials()
            if not smtp_user or not smtp_password:
                print(f"无法获取SMTP凭据，为 {recipient_email} 发送邮件失败")
                return False

            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = recipient_email
            msg['Subject'] = f'{date} OA通知汇总'
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port)
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient_email, msg.as_string())
            server.quit()

            print(f"成功发送 {date} 的邮件通知给 {recipient_email}")
            return True
        except Exception as e:
            print(f"为 {recipient_email} 发送邮件失败 ({file_path}): {e}")
            return False

    def _get_email_list(self) -> list[str]:
        try:
            recipient_file = self.config.recipient_list_file
            if not recipient_file.exists():
                print(f"{recipient_file} 文件不存在，请创建该文件并添加邮箱地址（每行一个）")
                return []

            with recipient_file.open('r', encoding='utf-8') as f:
                emails = [line.strip() for line in f if line.strip() and '@' in line]

            if not emails:
                print(f"{recipient_file} 文件中没有找到有效的邮箱地址")
                return []

            print(f"从 {recipient_file} 中读取到{len(emails)}个邮箱地址")
            return emails
        except Exception as e:
            print(f"读取邮箱列表时出错: {e}")
            return []

    def _locate_target_file(self) -> Path | None:
        if not self.events_dir.exists():
            print(f"目录 {self.events_dir} 不存在，请确保该目录已创建")
            return None

        json_files = sorted(self.events_dir.glob('*.json'))
        if not json_files:
            print(f"在 {self.events_dir} 目录中没有找到JSON文件")
            return None

        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        yesterday_file = self.events_dir / f"{yesterday.strftime('%Y-%m-%d')}.json"
        if yesterday_file.exists():
            print(f"找到前一天的JSON文件: {yesterday_file}")
            return yesterday_file

        json_files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        latest_file = json_files[0]
        print(f"未找到前一天文件，使用最新的JSON文件: {latest_file}")
        return latest_file

    def _process_new_files(self) -> None:
        try:
            target_file = self._locate_target_file()
            if not target_file:
                return

            email_list = self._get_email_list()
            if not email_list:
                return

            success_count = 0
            for email in email_list:
                if self._send_email(target_file, email):
                    success_count += 1

            print(f"邮件发送完成，成功: {success_count}/{len(email_list)}")
        except Exception as e:
            print(f"处理文件时出错: {e}")


if __name__ == '__main__':
    Sender().run()
