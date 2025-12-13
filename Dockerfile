# 使用官方轻量 Python 镜像
FROM python:3.9-slim

# 设置环境变量，确保日志和缓存行为规范
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. 核心系统库安装：这一步必须保证稳定和完整！
# 安装依赖：libglib2.0-0, libsm6, libxext6 是运行无头 OpenCV 经常需要的
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. 设置工作目录
WORKDIR /app

# 3. 安装 Python 依赖
# 升级 pip 和 setuptools 以确保构建环境干净
COPY requirements.txt .
RUN pip install --upgrade pip setuptools \
    && pip install --no-cache-dir -r requirements.txt

# 4. 复制应用程序代码
COPY . .

# 5. 启动命令
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
