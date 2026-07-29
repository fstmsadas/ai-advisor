-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS myapp;
USE myapp;

-- 系统指标表
CREATE TABLE IF NOT EXISTS system_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cpu_percent DECIMAL(5,2),
    memory_percent DECIMAL(5,2),
    disk_usage DECIMAL(5,2),
    load_avg DECIMAL(6,3),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_time (timestamp)
);

-- 日志统计表
CREATE TABLE IF NOT EXISTS log_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    log_date DATE NOT NULL,
    total_lines INT,
    error_count INT,
    warning_count INT,
    info_count INT,
    log_file VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date (log_date)
);

-- AI 建议表
CREATE TABLE IF NOT EXISTS ai_advice (
    id INT AUTO_INCREMENT PRIMARY KEY,
    advice_text TEXT NOT NULL,
    cpu_percent DECIMAL(5,2),
    memory_percent DECIMAL(5,2),
    disk_usage DECIMAL(5,2),
    load_avg DECIMAL(6,3),
    top_processes JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created (created_at)
);

-- 可选：如果已有 users 表，可保留；若无，可不创建或忽略
