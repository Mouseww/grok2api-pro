#!/usr/bin/env sh
set -eu

# ============================================
# Grok2API Docker 入口脚本
# ============================================

echo "============================================"
echo "  Grok2API Starting..."
echo "  Storage Mode: ${STORAGE_MODE:-file}"
echo "  Workers: ${WORKERS:-1}"
echo "============================================"

# 确保数据目录存在
mkdir -p /app/data /app/logs

# 检查配置文件
if [ ! -f /app/data/setting.toml ]; then
    echo "[Init] 配置文件不存在，从示例创建..."
    if [ -f /app/data/setting.example.toml ]; then
        cp /app/data/setting.example.toml /app/data/setting.toml
        echo "[Init] 配置文件已创建: /app/data/setting.toml"
    else
        echo "[Warn] 未找到配置示例文件，请手动创建配置"
    fi
fi

# 等待数据库就绪 (MySQL/Redis模式)
if [ "${STORAGE_MODE:-file}" = "mysql" ] && [ -n "${DATABASE_URL:-}" ]; then
    echo "[Init] 等待MySQL就绪..."
    # 简单等待，实际生产建议使用wait-for-it.sh
    sleep 5
fi

if [ "${STORAGE_MODE:-file}" = "redis" ] && [ -n "${DATABASE_URL:-}" ]; then
    echo "[Init] 等待Redis就绪..."
    sleep 2
fi

echo "[Init] 启动应用..."
exec "$@"

