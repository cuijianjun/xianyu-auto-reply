# Cookie 自动刷新功能部署指南

## 🚀 部署概述

本指南将帮助您在生产环境中部署和配置 Cookie 自动刷新功能，确保系统稳定、安全、高效运行。

## 📋 系统要求

### 最低要求

- **操作系统**: Linux (Ubuntu 18.04+, CentOS 7+) / macOS 10.15+ / Windows 10+
- **Python**: 3.8+
- **内存**: 2GB RAM
- **存储**: 10GB 可用空间
- **网络**: 稳定的互联网连接

### 推荐配置

- **操作系统**: Ubuntu 20.04 LTS
- **Python**: 3.9+
- **内存**: 4GB+ RAM
- **存储**: 50GB+ SSD
- **CPU**: 2 核心+
- **网络**: 100Mbps+ 带宽

## 🛠️ 安装步骤

### 1. 环境准备

#### Ubuntu/Debian

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装必要的系统依赖
sudo apt install -y python3 python3-pip python3-venv git curl wget

# 安装数据库 (SQLite已内置，如需MySQL/PostgreSQL)
sudo apt install -y sqlite3

# 安装进程管理器
sudo apt install -y supervisor
```

#### CentOS/RHEL

```bash
# 更新系统包
sudo yum update -y

# 安装必要的系统依赖
sudo yum install -y python3 python3-pip git curl wget

# 安装数据库
sudo yum install -y sqlite

# 安装进程管理器
sudo yum install -y supervisor
```

### 2. 项目部署

```bash
# 创建部署目录
sudo mkdir -p /opt/xianyu-auto-reply
cd /opt/xianyu-auto-reply

# 克隆项目 (或上传项目文件)
git clone https://github.com/your-repo/xianyu-auto-reply.git .

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装Python依赖
pip install -r requirements.txt

# 创建必要的目录
mkdir -p logs data static/uploads
```

### 3. 配置文件设置

#### 生产环境配置 (`global_config.yml`)

```yaml
# 基础配置
DEBUG: false
LOG_LEVEL: 'INFO'
SECRET_KEY: 'your-super-secret-key-change-this'

# 数据库配置
DATABASE:
  path: '/opt/xianyu-auto-reply/data/production.db'
  backup_path: '/opt/xianyu-auto-reply/data/backups'
  auto_backup: true
  backup_interval: 86400 # 24小时

# Cookie自动更新配置
COOKIE_AUTO_UPDATE:
  enabled: true
  refresh_interval: 3600 # 1小时
  retry_interval: 300 # 5分钟
  batch_size: 10 # 批量处理大小
  timeout: 30 # 请求超时
  max_retries: 3 # 最大重试次数
  concurrent_limit: 5 # 并发限制
  enable_notifications: true # 启用通知

  # 高级配置
  health_check_interval: 600 # 健康检查间隔
  cleanup_interval: 86400 # 清理间隔
  log_level: 'INFO'

  # 性能优化
  connection_pool_size: 20
  keep_alive_timeout: 30
  request_delay: 1 # 请求间延迟

# Web服务器配置
SERVER:
  host: '0.0.0.0'
  port: 8000
  workers: 4 # 工作进程数
  max_connections: 1000
  keepalive_timeout: 65

# 日志配置
LOGGING:
  level: 'INFO'
  file_path: '/opt/xianyu-auto-reply/logs'
  max_file_size: '100MB'
  backup_count: 10
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# 安全配置
SECURITY:
  api_token: 'your-api-token-change-this'
  allowed_hosts: ['localhost', '127.0.0.1', 'your-domain.com']
  cors_origins: ['https://your-frontend.com']
  rate_limit: 100 # 每分钟请求限制

# 监控配置
MONITORING:
  enable_metrics: true
  metrics_port: 9090
  health_check_path: '/health'
```

#### 环境变量配置 (`.env`)

```bash
# 生产环境标识
ENVIRONMENT=production

# 数据库配置
DATABASE_URL=sqlite:///opt/xianyu-auto-reply/data/production.db

# 安全配置
SECRET_KEY=your-super-secret-key-change-this
API_TOKEN=your-api-token-change-this

# 外部服务配置
REDIS_URL=redis://localhost:6379/0
WEBHOOK_SECRET=your-webhook-secret

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/opt/xianyu-auto-reply/logs/app.log
```

### 4. 数据库初始化

```bash
# 激活虚拟环境
source venv/bin/activate

# 初始化数据库
python -c "from db_manager import db_manager; print('数据库初始化完成')"

# 创建管理员用户 (如果需要)
python scripts/create_admin.py --username admin --email admin@example.com
```

### 5. 进程管理配置

#### Supervisor 配置 (`/etc/supervisor/conf.d/xianyu-auto-reply.conf`)

```ini
[program:xianyu-auto-reply]
command=/opt/xianyu-auto-reply/venv/bin/python Start.py
directory=/opt/xianyu-auto-reply
user=www-data
group=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/xianyu-auto-reply/logs/supervisor.log
stdout_logfile_maxbytes=100MB
stdout_logfile_backups=10
environment=ENVIRONMENT=production

[program:xianyu-cookie-updater]
command=/opt/xianyu-auto-reply/venv/bin/python -m utils.cookie_auto_updater
directory=/opt/xianyu-auto-reply
user=www-data
group=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/xianyu-auto-reply/logs/cookie-updater.log
stdout_logfile_maxbytes=100MB
stdout_logfile_backups=10
environment=ENVIRONMENT=production
```

#### 启动服务

```bash
# 重新加载Supervisor配置
sudo supervisorctl reread
sudo supervisorctl update

# 启动服务
sudo supervisorctl start xianyu-auto-reply
sudo supervisorctl start xianyu-cookie-updater

# 检查状态
sudo supervisorctl status
```

### 6. Nginx 反向代理配置

#### 安装 Nginx

```bash
sudo apt install -y nginx
```

#### Nginx 配置 (`/etc/nginx/sites-available/xianyu-auto-reply`)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL配置
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

    # 日志配置
    access_log /var/log/nginx/xianyu-auto-reply.access.log;
    error_log /var/log/nginx/xianyu-auto-reply.error.log;

    # 静态文件
    location /static/ {
        alias /opt/xianyu-auto-reply/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # API代理
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # 缓冲配置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;

        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }

    # 限制请求大小
    client_max_body_size 10M;
}
```

#### 启用站点

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/xianyu-auto-reply /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## 🔒 安全配置

### 1. 防火墙设置

```bash
# 安装UFW
sudo apt install -y ufw

# 配置防火墙规则
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 启用防火墙
sudo ufw enable
```

### 2. SSL 证书配置

#### 使用 Let's Encrypt

```bash
# 安装Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 设置自动续期
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. 用户权限配置

```bash
# 创建专用用户
sudo useradd -r -s /bin/false xianyu
sudo usermod -a -G www-data xianyu

# 设置文件权限
sudo chown -R xianyu:www-data /opt/xianyu-auto-reply
sudo chmod -R 750 /opt/xianyu-auto-reply
sudo chmod -R 640 /opt/xianyu-auto-reply/global_config.yml
```

## 📊 监控配置

### 1. 系统监控

#### 安装监控工具

```bash
# 安装htop和iotop
sudo apt install -y htop iotop

# 安装系统监控
sudo apt install -y prometheus-node-exporter
```

#### Prometheus 配置 (`prometheus.yml`)

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'xianyu-auto-reply'
    static_configs:
      - targets: ['localhost:9090']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### 2. 应用监控

#### 健康检查脚本 (`scripts/health_check.sh`)

```bash
#!/bin/bash

# 检查应用状态
check_app() {
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
    if [ "$response" = "200" ]; then
        echo "✅ 应用健康检查通过"
        return 0
    else
        echo "❌ 应用健康检查失败: HTTP $response"
        return 1
    fi
}

# 检查Cookie更新服务
check_cookie_service() {
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/cookie-auto-update/status)
    if [ "$response" = "200" ]; then
        echo "✅ Cookie更新服务正常"
        return 0
    else
        echo "❌ Cookie更新服务异常: HTTP $response"
        return 1
    fi
}

# 执行检查
check_app && check_cookie_service
```

#### 定时健康检查

```bash
# 添加到crontab
*/5 * * * * /opt/xianyu-auto-reply/scripts/health_check.sh >> /opt/xianyu-auto-reply/logs/health.log 2>&1
```

### 3. 日志监控

#### Logrotate 配置 (`/etc/logrotate.d/xianyu-auto-reply`)

```
/opt/xianyu-auto-reply/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 xianyu www-data
    postrotate
        supervisorctl restart xianyu-auto-reply
    endscript
}
```

## 🔄 备份策略

### 1. 数据库备份

#### 自动备份脚本 (`scripts/backup_db.sh`)

```bash
#!/bin/bash

BACKUP_DIR="/opt/xianyu-auto-reply/data/backups"
DB_PATH="/opt/xianyu-auto-reply/data/production.db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.db"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 备份数据库
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# 压缩备份文件
gzip "$BACKUP_FILE"

# 清理旧备份 (保留30天)
find "$BACKUP_DIR" -name "backup_*.db.gz" -mtime +30 -delete

echo "数据库备份完成: $BACKUP_FILE.gz"
```

#### 定时备份

```bash
# 每天凌晨2点备份
0 2 * * * /opt/xianyu-auto-reply/scripts/backup_db.sh
```

### 2. 配置文件备份

```bash
# 备份配置文件
tar -czf /opt/backups/xianyu-config-$(date +%Y%m%d).tar.gz \
    /opt/xianyu-auto-reply/global_config.yml \
    /opt/xianyu-auto-reply/.env \
    /etc/nginx/sites-available/xianyu-auto-reply \
    /etc/supervisor/conf.d/xianyu-auto-reply.conf
```

## 🚀 性能优化

### 1. 系统优化

#### 内核参数优化 (`/etc/sysctl.conf`)

```
# 网络优化
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_tw_buckets = 5000

# 内存优化
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# 文件描述符限制
fs.file-max = 65535
```

#### 应用生效

```bash
sudo sysctl -p
```

### 2. 应用优化

#### 数据库优化

```sql
-- 创建索引
CREATE INDEX IF NOT EXISTS idx_cookies_updated_at ON cookies(updated_at);
CREATE INDEX IF NOT EXISTS idx_cookie_status_enabled ON cookie_status(enabled);

-- 定期清理
DELETE FROM cookie_update_logs WHERE created_at < datetime('now', '-30 days');
```

#### 缓存配置

```yaml
# 在global_config.yml中添加
CACHE:
  enabled: true
  backend: 'redis'
  url: 'redis://localhost:6379/0'
  default_timeout: 300
  key_prefix: 'xianyu:'
```

## 🔧 故障排除

### 1. 常见问题

#### 服务无法启动

```bash
# 检查日志
sudo tail -f /opt/xianyu-auto-reply/logs/supervisor.log

# 检查端口占用
sudo netstat -tlnp | grep :8000

# 检查权限
ls -la /opt/xianyu-auto-reply/
```

#### Cookie 更新失败

```bash
# 检查网络连接
curl -I https://h5api.m.taobao.com

# 检查更新日志
tail -f /opt/xianyu-auto-reply/logs/cookie-updater.log

# 手动测试更新
python -c "from utils.cookie_auto_updater import cookie_auto_updater; print(cookie_auto_updater.test_connection())"
```

### 2. 性能问题

#### 内存使用过高

```bash
# 检查内存使用
free -h
ps aux --sort=-%mem | head

# 重启服务
sudo supervisorctl restart xianyu-auto-reply
```

#### 响应时间过长

```bash
# 检查数据库性能
sqlite3 /opt/xianyu-auto-reply/data/production.db "EXPLAIN QUERY PLAN SELECT * FROM cookies;"

# 检查网络延迟
ping h5api.m.taobao.com
```

## 📋 维护清单

### 日常维护

- [ ] 检查服务状态
- [ ] 查看错误日志
- [ ] 监控系统资源
- [ ] 验证备份完整性

### 周维护

- [ ] 清理过期日志
- [ ] 更新系统包
- [ ] 检查 SSL 证书
- [ ] 性能指标分析

### 月维护

- [ ] 数据库优化
- [ ] 安全更新
- [ ] 备份策略评估
- [ ] 容量规划

## 🆘 应急响应

### 服务中断处理

1. **立即响应** (5 分钟内)

   - 检查服务状态
   - 查看错误日志
   - 尝试重启服务

2. **问题诊断** (15 分钟内)

   - 分析根本原因
   - 检查系统资源
   - 确定影响范围

3. **恢复服务** (30 分钟内)
   - 实施修复措施
   - 验证服务正常
   - 通知相关人员

### 联系信息

- **技术支持**: support@example.com
- **紧急联系**: +86-xxx-xxxx-xxxx
- **监控告警**: alerts@example.com

---

**版本**: v1.0.0  
**更新时间**: 2025-09-13  
**维护团队**: DevOps 团队
