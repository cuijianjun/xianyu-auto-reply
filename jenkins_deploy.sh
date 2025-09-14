#!/bin/bash
# Jenkins部署脚本 - 安全版本

set -e  # 遇到错误立即退出

echo "🚀 Jenkins部署开始..."
echo "当前时间: $(date)"
echo "当前目录: $(pwd)"
echo "当前用户: $(whoami)"

# 1. 安全停止现有服务
echo "🛑 安全停止现有服务..."

# 查找并停止Python进程（更安全的方式）
PYTHON_PIDS=$(pgrep -f "python.*Start.py\|python.*reply_server.py" 2>/dev/null || true)
if [ -n "$PYTHON_PIDS" ]; then
    echo "找到运行中的Python进程: $PYTHON_PIDS"
    echo "$PYTHON_PIDS" | xargs -r kill -TERM 2>/dev/null || true
    sleep 5
    # 如果进程仍在运行，强制杀死
    REMAINING_PIDS=$(pgrep -f "python.*Start.py\|python.*reply_server.py" 2>/dev/null || true)
    if [ -n "$REMAINING_PIDS" ]; then
        echo "强制停止剩余进程: $REMAINING_PIDS"
        echo "$REMAINING_PIDS" | xargs -r kill -9 2>/dev/null || true
    fi
    echo "✅ Python服务已停止"
else
    echo "✅ 没有找到运行中的Python服务"
fi

# 2. 检查端口占用
echo "🔍 检查端口占用..."
PORT_8081=$(lsof -ti:8081 2>/dev/null || true)
if [ -n "$PORT_8081" ]; then
    echo "端口8081被占用，进程ID: $PORT_8081"
    kill -TERM $PORT_8081 2>/dev/null || true
    sleep 2
    # 如果仍被占用，强制杀死
    PORT_8081_REMAINING=$(lsof -ti:8081 2>/dev/null || true)
    if [ -n "$PORT_8081_REMAINING" ]; then
        kill -9 $PORT_8081_REMAINING 2>/dev/null || true
    fi
    echo "✅ 端口8081已释放"
else
    echo "✅ 端口8081未被占用"
fi

# 3. 验证修复文件
echo "🔍 验证修复文件..."
if [ ! -f "utils/token_manager.py" ]; then
    echo "❌ utils/token_manager.py 文件不存在"
    exit 1
fi

if [ ! -f "db_manager.py" ]; then
    echo "❌ db_manager.py 文件不存在"
    exit 1
fi

if [ ! -f "cookie_manager.py" ]; then
    echo "❌ cookie_manager.py 文件不存在"
    exit 1
fi

if [ ! -f "XianyuAutoAsync.py" ]; then
    echo "❌ XianyuAutoAsync.py 文件不存在"
    exit 1
fi

echo "✅ 所有关键文件存在"

# 4. 验证Python语法
echo "🔍 验证Python语法..."
python -m py_compile utils/token_manager.py || { echo "❌ utils/token_manager.py 语法错误"; exit 1; }
python -m py_compile db_manager.py || { echo "❌ db_manager.py 语法错误"; exit 1; }
python -m py_compile cookie_manager.py || { echo "❌ cookie_manager.py 语法错误"; exit 1; }
python -m py_compile XianyuAutoAsync.py || { echo "❌ XianyuAutoAsync.py 语法错误"; exit 1; }
python -m py_compile Start.py || { echo "❌ Start.py 语法错误"; exit 1; }
echo "✅ 所有Python文件语法正确"

# 5. 测试关键模块导入
echo "🔍 测试模块导入..."
python -c "
try:
    from db_manager import DatabaseManager
    from cookie_manager import CookieManager
    from XianyuAutoAsync import XianyuLive
    from utils.token_manager import XianyuTokenManager
    print('✅ 所有模块导入成功')
except Exception as e:
    print(f'❌ 模块导入失败: {e}')
    exit(1)
" || exit 1

# 6. 测试方法存在性
echo "🔍 测试方法存在性..."
python -c "
try:
    from utils.token_manager import XianyuTokenManager
    from cookie_manager import CookieManager
    
    tm = XianyuTokenManager()
    assert hasattr(tm, 'refresh_token'), 'refresh_token方法缺失'
    
    cm = CookieManager()
    assert hasattr(cm, 'start'), 'start方法缺失'
    assert hasattr(cm, 'stop'), 'stop方法缺失'
    
    print('✅ 所有方法存在')
except Exception as e:
    print(f'❌ 方法测试失败: {e}')
    exit(1)
" 2>/dev/null || exit 1

# 7. 启动服务
echo "🚀 启动服务..."

# 检查是否有虚拟环境
if [ -d ".venv" ]; then
    echo "使用虚拟环境启动..."
    source .venv/bin/activate
fi

# 后台启动服务
nohup python Start.py > logs/start.log 2>&1 &
START_PID=$!
echo "服务已启动，PID: $START_PID"

# 8. 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 9. 验证服务状态
echo "🔍 验证服务状态..."

# 检查进程是否还在运行
if kill -0 $START_PID 2>/dev/null; then
    echo "✅ 服务进程正在运行 (PID: $START_PID)"
else
    echo "❌ 服务进程已停止"
    echo "查看启动日志:"
    tail -20 logs/start.log 2>/dev/null || echo "无法读取启动日志"
    exit 1
fi

# 检查端口是否监听
sleep 5
if lsof -ti:8081 >/dev/null 2>&1; then
    echo "✅ 端口8081正在监听"
else
    echo "❌ 端口8081未监听"
    echo "查看启动日志:"
    tail -20 logs/start.log 2>/dev/null || echo "无法读取启动日志"
    exit 1
fi

# 10. 测试API接口
echo "🔍 测试API接口..."
sleep 5

# 测试健康检查接口
if curl -s -f http://localhost:8081/health >/dev/null 2>&1; then
    echo "✅ 健康检查接口正常"
else
    echo "⚠️  健康检查接口无响应（可能接口不存在，但服务可能正常）"
fi

# 测试根接口
if curl -s -f http://localhost:8081/ >/dev/null 2>&1; then
    echo "✅ 根接口正常"
else
    echo "⚠️  根接口无响应"
fi

echo "🎉 Jenkins部署完成！"
echo "📋 部署摘要:"
echo "  - 服务PID: $START_PID"
echo "  - 监听端口: 8081"
echo "  - 日志文件: logs/start.log"
echo "  - 部署时间: $(date)"

echo "📝 后续检查建议:"
echo "  1. 查看日志: tail -f logs/start.log"
echo "  2. 检查Cookie接口: curl http://localhost:8081/cookies/details"
echo "  3. 监控系统状态: ps aux | grep python"