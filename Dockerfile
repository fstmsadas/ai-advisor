FROM python:3.10-slim

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# 系统工具
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 安装依赖（无 DBUtils）
COPY requirements.txt .
RUN python -m pip install --upgrade pip && python -m pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY . .

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && usermod -aG adm appuser && chown -R appuser:appuser /app
USER appuser

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "--timeout", "240", "app:app"]
