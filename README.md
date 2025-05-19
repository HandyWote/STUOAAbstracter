# OAP 通知爬取与邮件发送系统

## 项目介绍

OAP是一个自动化的OA系统通知爬取与邮件发送系统，包含两个主要组件：

1. **OAP.py** - 负责爬取STUOA系统的通知，提取标题、发布单位、链接和内容摘要，并将处理后的数据保存为JSON文件
2. **Sender.py** - 负责读取JSON文件，将通知内容转换为HTML格式并通过邮件发送给订阅用户

## 系统要求

- Python 3.8+
- Windows/Linux/macOS

## 安装步骤

### 1. 克隆或下载项目

```bash
git clone <项目仓库地址>
# 或直接下载ZIP文件并解压
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

### 1. 创建key文件

在项目根目录创建一个名为`key`的文件（无扩展名），包含以下内容：

```
邮箱地址
邮箱密码或授权码
```

例如：
```
example@163.com
YOUR_PASSWORD_HERE
```

### 2. 创建List.txt文件

在项目根目录创建一个名为`List.txt`的文件，每行添加一个订阅者的邮箱地址：

```
user1@example.com
user2@example.com
user3@example.com
```

### 3. 创建events目录

确保项目根目录下存在`events`文件夹，用于存储爬取的通知数据：

```bash
mkdir events
```

## 使用方法

### 方法一：直接运行Python脚本

1. 爬取OA通知：

```bash
python OAP.py
```

2. 发送邮件通知：

```bash
python Sender.py
```

### 方法二：使用批处理文件（Windows）

1. 爬取OA通知：双击运行`runOAP.bat`
2. 发送邮件通知：双击运行`runSender.bat`

## 定时任务设置

### Windows系统

1. 打开任务计划程序
2. 创建基本任务
3. 设置触发器（如每天早上8点）
4. 操作选择"启动程序"
5. 程序/脚本选择批处理文件的完整路径（如`D:\Projects\Python\OAP\runOAP.bat`）

### Linux系统

使用crontab设置定时任务：

```bash
# 编辑crontab
crontab -e

# 添加以下内容（每天早上8点运行）
0 8 * * * cd /path/to/OAP && python OAP.py
30 8 * * * cd /path/to/OAP && python Sender.py
```

## 功能说明

### OAP.py

- 爬取OA系统通知
- 提取标题、发布单位、链接和内容
- 使用AI生成内容摘要
- 将数据保存为JSON文件（格式为`YYYY-MM-DD.json`）
- 支持上传JSON文件到服务器（需配置）

### Sender.py

- 读取前一天的JSON文件（如找不到则使用最新文件）
- 从List.txt读取订阅用户邮箱列表
- 生成美观的HTML邮件内容
- 通过SMTP发送邮件给所有订阅用户

## 常见问题

### 1. 邮件发送失败

- 检查key文件中的邮箱和密码是否正确
- 确认邮箱服务商是否允许SMTP访问
- 如使用163邮箱，请确保使用的是授权码而非登录密码

### 2. 爬取内容为空

- 检查OA系统是否可访问
- 确认网络连接正常
- 检查OA系统是否更改了页面结构

## 维护与更新

- 定期检查日志输出
- 确保key文件和List.txt的安全性
- 根据需要更新AI接口密钥

## 许可证

只开源技术，不允许跟我在学校抢生意QAQ