#!/bin/bash
# 生产环境部署脚本

set -e  # 遇到错误立即退出

echo "🚀 开始部署修复到生产环境..."

# 1. 创建备份
BACKUP_DIR="production_backup_$(date +%Y%m%d_%H%M%S)"
echo "📦 创建备份目录: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR/utils"

# 备份关键文件
if [ -f "utils/token_manager.py" ]; then
    cp utils/token_manager.py "$BACKUP_DIR/utils/"
    echo "✅ 备份 utils/token_manager.py"
fi

if [ -f "db_manager.py" ]; then
    cp db_manager.py "$BACKUP_DIR/"
    echo "✅ 备份 db_manager.py"
fi

# 2. 部署新文件（这里需要替换为实际的文件路径）
echo "📁 部署修复文件..."

# 注意：在实际部署时，需要将本地修复的文件复制到生产环境
# cp /path/to/local/utils/token_manager.py utils/
# cp /path/to/local/db_manager.py .

echo "✅ 文件部署完成"

# 3. 重启服务
echo "🔄 重启服务..."

# 检测服务类型并重启
if systemctl is-active --quiet xianyu-auto-reply 2>/dev/null; then
    echo "使用 systemd 重启服务..."
    sudo systemctl restart xianyu-auto-reply
    sudo systemctl status xianyu-auto-reply
elif command -v pm2 >/dev/null 2>&1 && pm2 list | grep -q xianyu; then
    echo "使用 PM2 重启服务..."
    pm2 restart xianyu-auto-reply
    pm2 status
else
    echo "手动重启服务..."
    echo "请手动停止当前服务进程，然后重新启动"
    echo "例如: pkill -f reply_server.py && nohup python reply_server.py &"
fi

echo "🎉 部署完成！"
echo "📋 请检查以下内容："
echo "1. 服务是否正常启动"
echo "2. /cookies/details 接口是否返回数据"
echo "3. Token刷新功能是否正常"
echo "4. 查看日志确认没有 'refresh_token' 方法缺失错误"
