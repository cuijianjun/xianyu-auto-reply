"""项目启动入口：

1. 创建 CookieManager，按配置文件 / 环境变量初始化账号任务
2. 在后台线程启动 FastAPI (reply_server) 提供管理与自动回复接口
3. 主协程保持运行
"""

import os
import sys
import asyncio
import threading
import uvicorn
from urllib.parse import urlparse
from pathlib import Path
from loguru import logger

# 修复Linux环境下的asyncio子进程问题
if sys.platform.startswith('linux'):
    try:
        # 在程序启动时就设置正确的事件循环策略
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        logger.debug("已设置事件循环策略以支持子进程")
    except Exception as e:
        logger.debug(f"设置事件循环策略失败: {e}")

from config import AUTO_REPLY, COOKIES_LIST
import cookie_manager as cm
from db_manager import db_manager
from file_log_collector import setup_file_logging
from usage_statistics import report_user_count
from utils.config_loader import cookie_auto_update_config


def _start_api_server():
    """后台线程启动 FastAPI 服务"""
    api_conf = AUTO_REPLY.get('api', {})

    # 优先使用环境变量配置
    host = os.getenv('API_HOST', '0.0.0.0')  # 默认绑定所有接口
    port = int(os.getenv('API_PORT', '8081'))  # 默认端口8081

    # 如果配置文件中有特定配置，则使用配置文件
    if 'host' in api_conf:
        host = api_conf['host']
    if 'port' in api_conf:
        port = api_conf['port']

    # 兼容旧的URL配置方式
    if 'url' in api_conf and 'host' not in api_conf and 'port' not in api_conf:
        url = api_conf.get('url', 'http://0.0.0.0:8080/xianyu/reply')
        parsed = urlparse(url)
        if parsed.hostname and parsed.hostname != 'localhost':
            host = parsed.hostname
        port = parsed.port or 8080

    logger.info(f"启动Web服务器: http://{host}:{port}")
    uvicorn.run("reply_server:app", host=host, port=port, log_level="info")


def load_keywords_file(path: str):
    """从文件读取关键字 -> [(keyword, reply)]"""
    kw_list = []
    p = Path(path)
    if not p.exists():
        return kw_list
    with p.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '\t' in line:
                k, r = line.split('\t', 1)
            elif ' ' in line:
                k, r = line.split(' ', 1)
            elif ':' in line:
                k, r = line.split(':', 1)
            else:
                continue
            kw_list.append((k.strip(), r.strip()))
    return kw_list


async def initialize_cookie_auto_update(manager):
    """初始化Cookie自动更新功能"""
    try:
        # 检查是否启用Cookie自动更新
        if not cookie_auto_update_config.is_enabled():
            logger.info("Cookie自动更新功能已禁用，跳过初始化")
            return
        
        logger.info("开始初始化Cookie自动更新功能...")
        
        # 检查是否应该自动启动
        if cookie_auto_update_config.should_auto_start():
            logger.info("配置为自动启动，为所有启用的账号启动Cookie自动更新")
            
            # 为所有启用的账号启动自动更新
            enabled_cookies = []
            for cookie_id, cookie_value in manager.cookies.items():
                if manager.cookie_status.get(cookie_id, True):  # 默认启用
                    enabled_cookies.append(cookie_id)
                    # 启用自动更新
                    success = manager.enable_cookie_auto_update(cookie_id)
                    if success:
                        logger.info(f"已为账号 {cookie_id} 启用Cookie自动更新")
                    else:
                        logger.warning(f"为账号 {cookie_id} 启用Cookie自动更新失败")
            
            logger.info(f"Cookie自动更新初始化完成，已启用 {len(enabled_cookies)} 个账号的自动更新")
        else:
            logger.info("配置为手动启动，Cookie自动更新功能已准备就绪")
        
        # 启动定时任务调度器
        await start_cookie_auto_update_scheduler(manager)
        
    except Exception as e:
        logger.error(f"初始化Cookie自动更新功能失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")


async def start_cookie_auto_update_scheduler(manager):
    """启动Cookie自动更新定时任务调度器"""
    try:
        logger.info("启动Cookie自动更新定时任务调度器...")
        
        # 创建后台任务来管理定时刷新
        async def cookie_auto_update_scheduler():
            """Cookie自动更新调度器主循环"""
            logger.info("Cookie自动更新调度器已启动")
            
            while True:
                try:
                    # 检查配置是否仍然启用
                    if not cookie_auto_update_config.is_enabled():
                        logger.debug("Cookie自动更新功能已禁用，调度器暂停")
                        await asyncio.sleep(60)  # 1分钟后重新检查
                        continue
                    
                    # 获取所有启用自动更新的账号
                    auto_update_accounts = []
                    for cookie_id in manager.cookies.keys():
                        if manager.is_cookie_auto_update_enabled(cookie_id):
                            auto_update_accounts.append(cookie_id)
                    
                    if auto_update_accounts:
                        logger.debug(f"调度器检查到 {len(auto_update_accounts)} 个账号启用了自动更新")
                        
                        # 这里不需要手动触发更新，因为CookieAutoUpdater内部已经有自己的定时循环
                        # 调度器主要用于监控和管理整体状态
                        
                        # 可以在这里添加一些监控逻辑，比如检查更新状态、清理过期任务等
                        await monitor_auto_update_status(manager, auto_update_accounts)
                    
                    # 等待下一次检查（每5分钟检查一次）
                    await asyncio.sleep(300)
                    
                except Exception as e:
                    logger.error(f"Cookie自动更新调度器运行异常: {e}")
                    await asyncio.sleep(60)  # 出错后等待1分钟再继续
        
        # 启动调度器任务
        scheduler_task = asyncio.create_task(cookie_auto_update_scheduler())
        logger.info("Cookie自动更新定时任务调度器启动成功")
        
        return scheduler_task
        
    except Exception as e:
        logger.error(f"启动Cookie自动更新定时任务调度器失败: {e}")
        raise


async def monitor_auto_update_status(manager, auto_update_accounts):
    """监控自动更新状态"""
    try:
        # 获取所有账号的自动更新状态
        status_dict = manager.get_cookie_auto_update_status()
        
        # 统计状态
        valid_tokens = 0
        invalid_tokens = 0
        
        for cookie_id in auto_update_accounts:
            if cookie_id in status_dict:
                status = status_dict[cookie_id]
                if status['token_valid']:
                    valid_tokens += 1
                else:
                    invalid_tokens += 1
        
        # 记录监控信息
        if auto_update_accounts:
            logger.debug(f"Cookie自动更新状态监控 - 总账号: {len(auto_update_accounts)}, "
                        f"有效Token: {valid_tokens}, 无效Token: {invalid_tokens}")
        
        # 如果有太多无效Token，可以考虑触发批量更新
        if invalid_tokens > len(auto_update_accounts) * 0.5:  # 超过50%的Token无效
            logger.warning(f"检测到大量无效Token ({invalid_tokens}/{len(auto_update_accounts)})，"
                          f"建议检查网络连接或账号状态")
    
    except Exception as e:
        logger.error(f"监控自动更新状态异常: {e}")


async def main():
    print("开始启动主程序...")

    # 初始化文件日志收集器
    print("初始化文件日志收集器...")
    setup_file_logging()
    logger.info("文件日志收集器已启动，开始收集实时日志")

    loop = asyncio.get_running_loop()

    # 创建 CookieManager 并在全局暴露
    print("创建 CookieManager...")
    cm.manager = cm.CookieManager(loop)
    manager = cm.manager
    print("CookieManager 创建完成")
    
    # 初始化Cookie自动更新功能
    print("初始化Cookie自动更新功能...")
    await initialize_cookie_auto_update(manager)
    print("Cookie自动更新功能初始化完成")

    # 1) 从数据库加载的 Cookie 已经在 CookieManager 初始化时完成
    # 为每个启用的 Cookie 启动任务
    for cid, val in manager.cookies.items():
        # 检查账号是否启用
        if not manager.get_cookie_status(cid):
            logger.info(f"跳过禁用的 Cookie: {cid}")
            continue

        task = None
        try:
            # 直接启动任务，不重新保存到数据库
            from db_manager import db_manager
            logger.info(f"正在获取Cookie详细信息: {cid}")
            cookie_info = db_manager.get_cookie_details(cid)
            user_id = cookie_info.get('user_id') if cookie_info else None
            logger.info(f"Cookie详细信息获取成功: {cid}, user_id: {user_id}")

            logger.info(f"正在创建异步任务: {cid}")
            task = loop.create_task(manager._run_xianyu(cid, val, user_id))
            manager.tasks[cid] = task
            logger.info(f"启动数据库中的 Cookie 任务: {cid} (用户ID: {user_id})")
            logger.info(f"任务已添加到管理器，当前任务数: {len(manager.tasks)}")
        except Exception as e:
            logger.error(f"启动 Cookie 任务失败: {cid}, {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            
            # 资源清理：如果任务已创建但添加到管理器失败，需要取消任务
            if task is not None and not task.done():
                logger.info(f"取消失败的任务: {cid}")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"任务已成功取消: {cid}")
                except Exception as cancel_error:
                    logger.error(f"取消任务时发生错误: {cid}, {cancel_error}")
            
            # 确保从管理器中移除失败的任务记录
            if cid in manager.tasks:
                logger.info(f"从管理器中移除失败的任务记录: {cid}")
                del manager.tasks[cid]
            
            # 标记Cookie为禁用状态，避免重复尝试
            manager.cookie_status[cid] = False
            logger.info(f"已将失败的Cookie标记为禁用: {cid}")
    
    # 2) 如果配置文件中有新的 Cookie，也加载它们
    for entry in COOKIES_LIST:
        cid = entry.get('id')
        val = entry.get('value')
        if not cid or not val or cid in manager.cookies:
            continue
        
        kw_file = entry.get('keywords_file')
        kw_list = load_keywords_file(kw_file) if kw_file else None
        manager.add_cookie(cid, val, kw_list)
        logger.info(f"从配置文件加载 Cookie: {cid}")

    # 3) 若老环境变量仍提供单账号 Cookie，则作为 default 账号
    env_cookie = os.getenv('COOKIES_STR')
    if env_cookie and 'default' not in manager.list_cookies():
        manager.add_cookie('default', env_cookie)
        logger.info("从环境变量加载 default Cookie")

    # 启动 API 服务线程
    print("启动 API 服务线程...")
    threading.Thread(target=_start_api_server, daemon=True).start()
    print("API 服务线程已启动")

    # 上报用户统计
    try:
        await report_user_count()
    except Exception as e:
        logger.debug(f"上报用户统计失败: {e}")

    # 阻塞保持运行
    print("主程序启动完成，保持运行...")
    await asyncio.Event().wait()


if __name__ == '__main__':
    asyncio.run(main()) 