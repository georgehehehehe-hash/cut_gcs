# --------------------------------------------------------------------------
# 阶段 1: 构建阶段 (安装所有依赖)
# --------------------------------------------------------------------------
FROM python:3.9-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. 安装系统库 (确保 OpenCV 运行)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装 Python 依赖
COPY requirements.txt .
RUN pip install --upgrade pip setuptools \
    && pip install --no-cache-dir -r requirements.txt
    
# --------------------------------------------------------------------------
# 阶段 2: 运行时阶段 (精简环境)
# --------------------------------------------------------------------------
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 关键修复: 复制 Python 库和由 pip 创建的可执行文件
# 1. 复制由 pip 生成的 /usr/local/bin 中的可执行文件 (如 gunicorn)
COPY --from=builder /usr/local/bin /usr/local/bin

# 2. 复制所有 Python 库
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

# 3. 复制系统共享库和链接 (确保 OpenCV 找到依赖)
COPY --from=builder /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu

# 复制应用程序代码
COPY . .

# 启动命令 (使用 Gunicorn)
CMD exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:${PORT}
