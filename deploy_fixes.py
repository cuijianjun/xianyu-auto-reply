#!/usr/bin/env python3
"""
部署修复脚本 - 确保生产环境获得正确的修复
"""

import os
import sys
import shutil
from datetime import datetime

def create_backup():
    """创建备份"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup_{timestamp}"
    
    print(f"📦 创建备份目录: {backup_dir}")
    
    # 备份关键文件
    files_to_backup = [
        'utils/token_manager.py',
        'db_manager.py',
        'XianyuAutoAsync.py'
    ]
    
    os.makedirs(backup_dir, exist_ok=True)
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            # 创建目录结构
            backup_file_path = os.path.join(backup_dir, file_path)
            os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
            
            # 复制文件
            shutil.copy2(file_path, backup_file_path)
            print(f"✅ 备份: {file_path} -> {backup_file_path}")
        else:
            print(f"⚠️  文件不存在: {file_path}")
    
    return backup_dir

def verify_fixes():
    """验证修复内容"""
    print("\n🔍 验证修复内容...")
    
    fixes_verified = True
    
    # 1. 检查Token管理器的refresh_token方法
    try:
        with open('utils/token_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'async def refresh_token(self, cookie_id: str = None)' in content:
            print("✅ Token管理器 refresh_token 方法存在")
        else:
            print("❌ Token管理器 refresh_token 方法缺失")
            fixes_verified = False
            
    except Exception as e:
        print(f"❌ 检查Token管理器失败: {e}")
        fixes_verified = False
    
    # 2. 检查数据库兼容性修复
    try:
        with open('db_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'PRAGMA table_info(cookies)' in content and 'cookie_column = \'cookie\' if \'cookie\' in column_names else \'value\'' in content:
            print("✅ 数据库兼容性修复存在")
        else:
            print("❌ 数据库兼容性修复缺失")
            fixes_verified = False
            
    except Exception as e:
        print(f"❌ 检查数据库修复失败: {e}")
        fixes_verified = False
    
    return fixes_verified

def generate_production_deployment_script():
    """生成生产环境部署脚本"""
    script_content = '''#!/bin/bash
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
'''
    
    with open('deploy_to_production.sh', 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # 设置执行权限
    os.chmod('deploy_to_production.sh', 0o755)
    
    print("✅ 生成生产环境部署脚本: deploy_to_production.sh")

def main():
    """主函数"""
    print("🚀 准备部署修复...")
    
    # 1. 创建备份
    backup_dir = create_backup()
    
    # 2. 验证修复
    if not verify_fixes():
        print("❌ 修复验证失败，请检查修复内容")
        return False
    
    # 3. 生成部署脚本
    generate_production_deployment_script()
    
    print(f"\n📋 部署准备完成！")
    print(f"📦 备份目录: {backup_dir}")
    print(f"📁 部署脚本: deploy_to_production.sh")
    
    print(f"\n🎯 接下来的步骤:")
    print(f"1. 将以下文件上传到生产环境:")
    print(f"   - utils/token_manager.py")
    print(f"   - db_manager.py")
    print(f"   - deploy_to_production.sh")
    print(f"2. 在生产环境运行: chmod +x deploy_to_production.sh && ./deploy_to_production.sh")
    print(f"3. 检查服务状态和日志")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)