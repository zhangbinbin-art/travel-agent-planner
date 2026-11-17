FROM python:3.12-slim

# onnxruntime（fastembed 依赖）需要 libgomp1；curl 用于容器健康检查
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# 启动前建表（幂等），再启动服务
CMD ["sh", "-c", "python scripts/create_tables.py && uvicorn main:app --host 0.0.0.0 --port 8000"]
