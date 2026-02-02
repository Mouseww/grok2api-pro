# ============================================
# Grok2API Dockerfile
# 多阶段构建，优化镜像大小
# ============================================

# 构建阶段
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# 安装构建依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/build/deps -r requirements.txt

# ============================================
# 运行阶段
# ============================================
FROM python:3.11-slim AS runtime

# 元数据
LABEL maintainer="Grok2API Team" \
      version="1.3.1" \
      description="Grok2API - OpenAI Compatible API for Grok"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/deps:$PYTHONPATH \
    # 默认配置
    TZ=Asia/Shanghai \
    STORAGE_MODE=file \
    WORKERS=1

WORKDIR /app

# 安装运行时依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        tzdata \
    && rm -rf /var/lib/apt/lists/* \
    # 创建非root用户
    && groupadd -r grok2api \
    && useradd -r -g grok2api grok2api \
    # 创建数据目录
    && mkdir -p /app/data /app/logs \
    && chown -R grok2api:grok2api /app

# 从构建阶段复制依赖
COPY --from=builder /build/deps /app/deps

# 复制应用代码
COPY --chown=grok2api:grok2api . /app

# 复制并设置入口脚本
COPY --chown=grok2api:grok2api docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# 切换到非root用户
USER grok2api

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 入口点
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# 默认命令 (支持通过环境变量配置workers)
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-1}"]
