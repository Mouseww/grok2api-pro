-- Grok2API MySQL 初始化脚本
-- 此脚本在MySQL容器首次启动时自动执行

-- 设置字符集
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 确保数据库使用正确的字符集
ALTER DATABASE grok2api CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- 创建Token表
CREATE TABLE IF NOT EXISTS grok_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    data JSON NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建配置表
CREATE TABLE IF NOT EXISTS grok_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    data JSON NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建调用日志表 (可选，用于更高效的日志查询)
CREATE TABLE IF NOT EXISTS grok_call_logs (
    id VARCHAR(36) PRIMARY KEY,
    timestamp BIGINT NOT NULL,
    sso VARCHAR(255),
    sso_full TEXT,
    model VARCHAR(100),
    success BOOLEAN DEFAULT TRUE,
    status_code INT,
    token_consumed INT DEFAULT 1,
    response_time FLOAT,
    error_message TEXT,
    proxy_used VARCHAR(255),
    media_urls JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp),
    INDEX idx_sso (sso),
    INDEX idx_model (model),
    INDEX idx_success (success)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建视频任务表 (可选，用于视频生成任务持久化)
CREATE TABLE IF NOT EXISTS grok_video_tasks (
    id VARCHAR(36) PRIMARY KEY,
    status VARCHAR(20) NOT NULL,
    prompt TEXT,
    model VARCHAR(100),
    size VARCHAR(20),
    n_seconds INT,
    aspect_ratio VARCHAR(10),
    created_at BIGINT NOT NULL,
    completed_at BIGINT,
    failed_at BIGINT,
    progress INT DEFAULT 0,
    output_url TEXT,
    error_code VARCHAR(50),
    error_message TEXT,
    metadata JSON,
    sso VARCHAR(255),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_sso (sso)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 输出初始化完成信息
SELECT 'Grok2API database initialized successfully!' AS message;
