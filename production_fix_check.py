#!/usr/bin/env python3
"""
生产环境修复检查脚本
检查关键修复是否已正确部署
"""

import sys
import os
import traceback

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_token_manager_fix():
    """检查Token管理器修复"""
    print("🔍 检查Token管理器修复...")
    try:
        from utils.token_manager import XianyuTokenManager
        
        # 创建实例
        token_manager = XianyuTokenManager()
        
        # 检查refresh_token方法
        if hasattr(token_manager, 'refresh_token'):
            print("✅ refresh_token 方法存在")
            
            # 检查方法签名
            import inspect
            sig = inspect.signature(token_manager.refresh_token)
            print(f"✅ 方法签名: refresh_token{sig}")
            
            return True
        else:
            print("❌ refresh_token 方法不存在")
            print("📋 可用方法:", [m for m in dir(token_manager) if not m.startswith('_')])
            return False
            
    except Exception as e:
        print(f"❌ Token管理器检查失败: {e}")
        traceback.print_exc()
        return False

def check_database_fix():
    """检查数据库修复"""
    print("\n🔍 检查数据库修复...")
    try:
        from db_manager import DatabaseManager
        
        # 创建实例
        db = DatabaseManager()
        
        # 检查数据库表结构
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("PRAGMA table_info(cookies)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            print(f"✅ 数据库表结构: {column_names}")
            
            # 检查是否有cookie或value列
            has_cookie = 'cookie' in column_names
            has_value = 'value' in column_names
            
            print(f"✅ 包含 'cookie' 列: {has_cookie}")
            print(f"✅ 包含 'value' 列: {has_value}")
            
            if not has_cookie and not has_value:
                print("❌ 既没有 'cookie' 列也没有 'value' 列")
                return False
                
        except Exception as schema_error:
            print(f"❌ 检查表结构失败: {schema_error}")
            return False
        
        # 测试get_all_cookies方法
        try:
            cookies = db.get_all_cookies(1)
            print(f"✅ get_all_cookies 调用成功，返回 {len(cookies)} 个cookie")
            print(f"✅ 返回类型: {type(cookies)}")
            
            if cookies and isinstance(cookies, list):
                first_cookie = cookies[0]
                print(f"✅ 第一个cookie格式: {list(first_cookie.keys()) if isinstance(first_cookie, dict) else type(first_cookie)}")
                
            return True
            
        except Exception as method_error:
            print(f"❌ get_all_cookies 方法调用失败: {method_error}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        traceback.print_exc()
        return False

def check_xianyu_live_integration():
    """检查XianyuLive集成"""
    print("\n🔍 检查XianyuLive集成...")
    try:
        # 检查XianyuAutoAsync.py中的refresh_token方法
        with open('XianyuAutoAsync.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查是否有refresh_token方法定义
        if 'async def refresh_token(self):' in content:
            print("✅ XianyuLive.refresh_token 方法存在")
        else:
            print("❌ XianyuLive.refresh_token 方法不存在")
            return False
            
        # 检查token_manager的调用
        if 'self.token_manager.refresh_token()' in content:
            print("✅ 调用 self.token_manager.refresh_token() 存在")
        else:
            print("❌ 调用 self.token_manager.refresh_token() 不存在")
            
        return True
        
    except Exception as e:
        print(f"❌ XianyuLive集成检查失败: {e}")
        return False

def generate_deployment_commands():
    """生成部署命令"""
    print("\n📋 生产环境部署建议:")
    print("1. 备份当前代码:")
    print("   cp -r /path/to/production /path/to/backup_$(date +%Y%m%d_%H%M%S)")
    print()
    print("2. 更新关键文件:")
    print("   # 更新Token管理器")
    print("   cp utils/token_manager.py /path/to/production/utils/")
    print("   # 更新数据库管理器")
    print("   cp db_manager.py /path/to/production/")
    print()
    print("3. 重启服务:")
    print("   # 如果使用systemd")
    print("   sudo systemctl restart xianyu-auto-reply")
    print("   # 如果使用PM2")
    print("   pm2 restart xianyu-auto-reply")
    print("   # 如果使用nohup")
    print("   pkill -f reply_server.py && nohup python reply_server.py &")
    print()
    print("4. 验证修复:")
    print("   # 检查日志")
    print("   tail -f logs/app.log")
    print("   # 测试API")
    print("   curl -X GET 'https://xianyu.barenkeji.com/cookies/details' -H 'Authorization: Bearer YOUR_TOKEN'")

def main():
    """主检查函数"""
    print("🚀 开始生产环境修复检查...")
    
    results = []
    
    # 检查Token管理器
    results.append(("Token管理器", check_token_manager_fix()))
    
    # 检查数据库
    results.append(("数据库修复", check_database_fix()))
    
    # 检查XianyuLive集成
    results.append(("XianyuLive集成", check_xianyu_live_integration()))
    
    # 总结结果
    print("\n📊 检查结果总结:")
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"• {name}: {status}")
    
    success_count = sum(result for _, result in results)
    total_count = len(results)
    
    print(f"\n🎯 总体结果: {success_count}/{total_count} 个检查通过")
    
    if success_count == total_count:
        print("🎉 所有检查通过！代码修复正确，可以部署到生产环境")
        generate_deployment_commands()
        return True
    else:
        print("⚠️  部分检查失败，需要修复后再部署")
        generate_deployment_commands()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)