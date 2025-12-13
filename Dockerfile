# --------------------------------------------------------------------------
# 阶段 1: 构建阶段 (安装所有依赖)
# --------------------------------------------------------------------------
FROM python:3.9-slim as builder

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. 安装 OpenCV 所需的系统库
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    # 安装 git 是为了确保所有 pip 依赖都能顺利安装（尽管不总是必需，但可防范问题）
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装 Python 依赖
COPY requirements.txt .
# 升级构建工具并安装所有依赖
RUN pip install --upgrade pip setuptools \
    && pip install --no-cache-dir -r requirements.txt
    
# --------------------------------------------------------------------------
# 阶段 2: 运行时阶段 (使用精简环境)
# --------------------------------------------------------------------------
FROM python:3.9-slim

# 从构建阶段复制系统库和 Python 库
COPY --from=builder /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

# 设置工作目录
WORKDIR /app

# 复制应用程序代码
COPY . .

# 启动命令
# 替换为 (使用 Gunicorn 启动 Uvicorn workers):
CMD exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:${PORT}
