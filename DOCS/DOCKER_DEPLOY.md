# Grok2API Docker 部署指南

本文档介绍如何使用 Docker 部署 Grok2API。

## 📋 前置要求

- Docker Engine 20.10+
- Docker Compose v2.0+
- 至少 1GB 可用内存
- 开放端口 8001（或自定义端口）

## 🚀 快速开始

### 1. 基础部署（文件存储）

最简单的部署方式，适合单机/测试环境：

```bash
# 1. 准备配置文件
cp data/setting.example.toml data/setting.toml
# 编辑 data/setting.toml 填入必要配置

# 2. 构建并启动
docker-compose up -d

# 3. 查看日志
docker-compose logs -f grok2api

# 4. 访问服务
curl http://localhost:8001/health
```

### 2. MySQL 存储模式

适合需要持久化存储和多进程部署的场景：

```bash
# 1. 配置环境变量
cp .env.example .env

# 2. 编辑 .env 文件
cat > .env << EOF
PORT=8001
STORAGE_MODE=mysql
WORKERS=4
DATABASE_URL=mysql://grok2api:grok2api_password@mysql:3306/grok2api
MYSQL_ROOT_PASSWORD=your_root_password
MYSQL_PASSWORD=your_password
EOF

# 3. 启动服务（含MySQL）
docker-compose --profile mysql up -d

# 4. 验证数据库连接
docker-compose exec mysql mysql -u grok2api -p -e "SHOW DATABASES;"
```

### 3. Redis 存储模式

适合高性能缓存需求：

```bash
# 1. 配置环境变量
cat > .env << EOF
PORT=8001
STORAGE_MODE=redis
WORKERS=2
DATABASE_URL=redis://redis:6379/0
EOF

# 2. 启动服务（含Redis）
docker-compose --profile redis up -d
```

### 4. 生产环境完整部署

使用 MySQL + Redis + Nginx 的完整生产部署：

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 设置所有密码

# 2. 准备SSL证书（可选）
# 将证书放入 docker/nginx/ssl/

# 3. 启动完整服务栈
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. 查看所有服务状态
docker-compose ps
```

## ⚙️ 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PORT` | 服务端口 | `8001` |
| `STORAGE_MODE` | 存储模式 (file/mysql/redis) | `file` |
| `WORKERS` | 工作进程数 | `1` |
| `DATABASE_URL` | 数据库连接URL | - |
| `TZ` | 时区 | `Asia/Shanghai` |

### 存储模式对比

| 特性 | file | mysql | redis |
|------|------|-------|-------|
| 配置复杂度 | 低 | 中 | 中 |
| 持久化 | ✅ | ✅ | ✅ |
| 多进程支持 | ⚠️ | ✅ | ✅ |
| 查询性能 | 低 | 高 | 极高 |
| 适用场景 | 单机/测试 | 生产 | 高并发 |

## 📁 目录结构

```
├── docker-compose.yml          # 基础编排文件
├── docker-compose.prod.yml     # 生产环境扩展
├── Dockerfile                  # 镜像构建文件
├── docker-entrypoint.sh        # 容器入口脚本
├── .env.example                # 环境变量示例
├── .dockerignore               # 构建忽略文件
└── docker/
    ├── mysql/
    │   └── init/
    │       └── 01-init.sql     # MySQL初始化脚本
    └── nginx/
        ├── nginx.conf          # Nginx配置
        └── ssl/
            └── README.md       # SSL证书说明
```

## 🔧 常用命令

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f [服务名]

# 重启服务
docker-compose restart [服务名]

# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v

# 进入容器
docker-compose exec grok2api sh

# 查看服务状态
docker-compose ps

# 更新镜像并重启
docker-compose pull && docker-compose up -d
```

## 🔒 安全建议

### 1. 更改默认密码

```bash
# 编辑 .env 文件，修改以下变量：
MYSQL_ROOT_PASSWORD=<强密码>
MYSQL_PASSWORD=<强密码>
```

### 2. 配置防火墙

```bash
# 仅开放必要端口
ufw allow 8001/tcp    # API端口
ufw allow 80/tcp      # HTTP (如果使用Nginx)
ufw allow 443/tcp     # HTTPS (如果使用Nginx)
```

### 3. 使用HTTPS

1. 获取SSL证书（Let's Encrypt或商业证书）
2. 将证书放入 `docker/nginx/ssl/`
3. 编辑 `docker/nginx/nginx.conf` 取消HTTPS配置注释
4. 重启Nginx容器

### 4. 限制资源

在 `docker-compose.prod.yml` 中已配置资源限制：

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

## 🐛 故障排除

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs grok2api

# 检查配置文件
docker-compose exec grok2api cat /app/data/setting.toml
```

### 数据库连接失败

```bash
# 检查MySQL状态
docker-compose --profile mysql ps

# 手动测试连接
docker-compose exec mysql mysql -u grok2api -p -e "SELECT 1;"
```

### 端口被占用

```bash
# 查看端口占用
netstat -tlnp | grep 8001

# 修改端口
# 编辑 .env 文件：PORT=8002
```

### 权限问题

```bash
# 修复数据目录权限
sudo chown -R 1000:1000 ./data ./logs
```

## 📊 监控与日志

### 查看实时日志

```bash
docker-compose logs -f --tail=100 grok2api
```

### 健康检查

```bash
# API健康检查
curl http://localhost:8001/health

# 容器健康状态
docker inspect --format='{{.State.Health.Status}}' grok2api
```

### 资源使用

```bash
# 查看资源使用
docker stats grok2api

# 查看磁盘使用
docker system df
```

## 🔄 升级指南

```bash
# 1. 备份数据
cp -r ./data ./data.backup

# 2. 拉取最新代码
git pull

# 3. 重新构建镜像
docker-compose build --no-cache

# 4. 滚动更新
docker-compose up -d

# 5. 验证服务
curl http://localhost:8001/health
```

## 📝 更多资源

- [项目主页](https://github.com/your-repo/grok2api)
- [API文档](./readme.md)
- [配置参考](./data/setting.example.toml)
- [更新日志](./CHANGELOG.md)
