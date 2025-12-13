# 使用官方 Python 3.9 镜像
FROM python:3.9

# 设置环境变量，确保 Python 链接和路径正确
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. 安装必要的系统库
# 必须使用完整的 python:3.9 镜像来确保 apt-get 正常
# 我们将安装 OpenCV 核心依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. 设置工作目录
WORKDIR /app

# 3. 安装 Python 依赖
COPY requirements.txt .
# 升级构建工具并安装所有依赖
RUN pip install --upgrade pip setuptools \
    && pip install --no-cache-dir -r requirements.txt
    
# 4. 复制应用程序代码
COPY . .

# 5. 启动命令 (使用 Gunicorn)
# Gunicorn 在完整的 Python 镜像中应该能正确找到路径
CMD exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:${PORT}
