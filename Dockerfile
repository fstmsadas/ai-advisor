FROM python:3.10-slim

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# 安装系统工具（curl 用于健康检查）
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 复制全部源码
COPY . .

# 创建非 root 用户（安全）
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 默认启动 Gunicorn（Flask 应用）
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
