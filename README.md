# OAP Notification Pipeline

> **许可提醒**：本项目仅限非商业用途。任何基于本项目的源码或二次发布必须显著保留原作者 "OAP Notification Pipeline" 标识及关键署名信息。

## 关于项目

该仓库抓取汕头大学 OA 门户的公告、调用大模型生成摘要，并通过邮件发送给订阅者。核心组件：
- `spider/OAP.py`：按日期抓取公告并生成 `events/<date>.json`；支持 `--date YYYY-MM-DD` 指定目标日，默认抓取当天。
- `sender/Sender.py`：加载指定日期的事件文件，组装邮件模板并投递；同样支持 `--date`（默认昨日）。
- `main.py`：串联爬虫与邮件，默认处理昨日数据，便于定时任务调用。
- `config/config.py`：统一配置读取与目录管理。

生成的事件文件存放在 `events/`，SMTP 凭据放在 `key/`（两者请勿提交）。

## 快速开始

```bash
uv sync
cp env.example env   # 补充 SMTP 账号、AI KEY 等
uv run python main.py --date 2025-09-25  # 验证单日流程
```

默认会写入 `events/2025-09-25.json`，随后发送邮件到 `List.txt` 中列出的地址。部署前请把真实邮箱换成安全的占位符，避免误发。

## Docker 与计划任务

项目自带 Dockerfile 与 `docker-compose.yml`：

```bash
docker compose up -d --build
docker compose logs -f oap
```

容器内置 cron，每天 06:00（默认 `Asia/Shanghai`）执行 `/app/main.py`。日志写入 `/var/log/oap.log`，可通过 `docker logs` 查看。若需调整时间或添加环境变量，可修改 `docker/cronjob`、`docker/run_oap.sh` 或 compose 中的挂载。

## 本地定时示例（可选）

- Linux/macOS：`0 6 * * * cd /path/to/OAP && uv run python main.py`
- Windows：使用“任务计划程序”，触发器设为每日 06:00，操作指向 `uv run python main.py`。

## 贡献指南

欢迎提交改进建议或补丁：
1. Fork & 新建分支。
2. `uv run python main.py --date YYYY-MM-DD` 验证流程。
3. 通过 Pull Request 描述变更、验证结果与样例输出（勿包含真实数据）。

## 使用限制与署名

- **禁止商业用途**：不得将本项目或衍生作品用于任何盈利、收费或商业化场景。
- **保留原作者信息**：对源码的修改、再分发或线上部署必须保留原作者及项目名称标识，包括但不限于 README 顶部的声明。
- 如需商业合作或授权，请联系原作者获得书面许可。

