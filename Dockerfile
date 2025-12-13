# 使用官方轻量 Python 镜像
FROM python:3.9-slim

# 设置环境变量，防止 Python 生成 .pyc 文件，并让日志直接输出
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. 安装 OpenCV 运行所需的系统依赖
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. 设置工作目录
WORKDIR /app

# 3. 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 复制应用程序代码
COPY . .

# 5. 启动命令
# Cloud Run 会自动注入 PORT 环境变量，必须监听这个端口
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}