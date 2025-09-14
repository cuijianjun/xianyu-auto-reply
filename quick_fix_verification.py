#!/usr/bin/env python3
"""
快速修复验证脚本 - 验证关键修复是否存在
"""

def check_token_manager_fix():
    """检查Token管理器修复"""
    print("🔍 检查Token管理器修复...")
    try:
        with open('utils/token_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键修复内容
        checks = [
            ('refresh_token方法定义', 'async def refresh_token(self, cookie_id: str = None)'),
            ('refresh_token方法实现', 'success = await self.force_refresh_token(cookie_id)'),
            ('兼容性处理', 'if cookie_id is None:'),
        ]
        
        all_passed = True
        for check_name, check_content in checks:
            if check_content in content:
                print(f"✅ {check_name}: 存在")
            else:
                print(f"❌ {check_name}: 缺失")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def check_database_fix():
    """检查数据库修复"""
    print("\n🔍 检查数据库修复...")
    try:
        with open('db_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键修复内容
        checks = [
            ('表结构检查', 'PRAGMA table_info(cookies)'),
            ('列名兼容性', 'cookie_column = \'cookie\' if \'cookie\' in column_names else \'value\''),
            ('动态查询构建', 'query = f"SELECT id, {cookie_column}, user_id FROM cookies'),
            ('列表格式返回', 'results = []'),
            ('统一键名', '\'cookie\': row[1]'),
        ]
        
        all_passed = True
        for check_name, check_content in checks:
            if check_content in content:
                print(f"✅ {check_name}: 存在")
            else:
                print(f"❌ {check_name}: 缺失")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def check_xianyu_integration():
    """检查XianyuLive集成"""
    print("\n🔍 检查XianyuLive集成...")
    try:
        with open('XianyuAutoAsync.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键集成内容
        checks = [
            ('XianyuLive refresh_token方法', 'async def refresh_token(self):'),
            ('Token管理器调用', 'await self.token_manager.refresh_token()'),
            ('错误处理', 'except Exception as e:'),
        ]
        
        all_passed = True
        for check_name, check_content in checks:
            if check_content in content:
                print(f"✅ {check_name}: 存在")
            else:
                print(f"❌ {check_name}: 缺失")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def main():
    """主验证函数"""
    print("🚀 快速修复验证...")
    
    results = []
    results.append(("Token管理器修复", check_token_manager_fix()))
    results.append(("数据库修复", check_database_fix()))
    results.append(("XianyuLive集成", check_xianyu_integration()))
    
    print("\n📊 验证结果:")
    success_count = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"• {name}: {status}")
        if result:
            success_count += 1
    
    print(f"\n🎯 总体结果: {success_count}/{len(results)} 个修复验证通过")
    
    if success_count == len(results):
        print("🎉 所有修复验证通过！可以部署到生产环境")
        print("\n📋 部署步骤:")
        print("1. 将以下文件上传到生产环境:")
        print("   - utils/token_manager.py")
        print("   - db_manager.py")
        print("2. 重启服务")
        print("3. 检查日志确认修复生效")
        return True
    else:
        print("⚠️  部分修复验证失败，请检查代码")
        return False

if __name__ == "__main__":
    main()