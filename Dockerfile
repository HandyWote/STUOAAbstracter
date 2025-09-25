FROM docker.1ms.run/python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN set -eux; \
    codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"; \
    rm -f /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; \
    echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian ${codename} main contrib non-free non-free-firmware" > /etc/apt/sources.list; \
    echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian ${codename}-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list; \
    echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian-security ${codename}-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

RUN apt-get update \
    && apt-get install -y --no-install-recommends cron ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

ENV PATH="/app/.venv/bin:$PATH"

COPY . ./

RUN chmod +x docker/run_oap.sh docker/entrypoint.sh

ENTRYPOINT ["/app/docker/entrypoint.sh"]
