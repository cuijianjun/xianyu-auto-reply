from __future__ import annotations
import asyncio
import time
from typing import Dict, List, Tuple, Optional, Union
from loguru import logger
from db_manager import db_manager
from utils.logger import LoggerManager, TraceContext
from utils.cookie_auto_updater import cookie_auto_updater
from utils.token_manager import token_manager

__all__ = ["CookieManager", "manager"]


class CookieManager:
    """管理多账号 Cookie 及其对应的 XianyuLive 任务和关键字"""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.cookies: Dict[str, str] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.keywords: Dict[str, List[Tuple[str, str]]] = {}
        self.logger_manager = LoggerManager("CookieManager")
        self.cookie_status: Dict[str, bool] = {}  # 账号启用状态
        self.auto_confirm_settings: Dict[str, bool] = {}  # 自动确认发货设置
        self.auto_update_enabled: Dict[str, bool] = {}  # Cookie自动更新启用状态
        self.cookie_refresh_timers: Dict[str, asyncio.Task] = {}  # Cookie定时刷新任务
        self.cookie_last_refresh: Dict[str, float] = {}  # 最后刷新时间戳
        self.trace_id = TraceContext.generate_trace_id()  # 管理器级别的追踪ID
        self.logger = LoggerManager("CookieManager").get_logger()
        self._load_from_db()
        self._start_refresh_tasks()
        
        # 初始化Cookie自动更新器
        self._init_auto_updater()
        
        # 初始化Token管理器
        self._init_token_manager()
        
    def _start_refresh_tasks(self):
        """启动所有Cookie的定时刷新任务"""
        self.logger.info("开始启动Cookie定时刷新任务")
        for cookie_id in self.cookies:
            if self.cookie_status.get(cookie_id, True):
                self._start_cookie_refresh_task(cookie_id)
        self.logger.info(f"已启动 {len(self.cookies)} 个Cookie的定时刷新任务")
        
    def _start_cookie_refresh_task(self, cookie_id: str):
        """启动单个Cookie的定时刷新任务"""
        if cookie_id in self.cookie_refresh_timers:
            self.logger.warning(f"Cookie {cookie_id} 的刷新任务已存在，跳过启动")
            return
            
        async def refresh_cookie_periodically():
            """定时刷新Cookie的协程任务"""
            refresh_interval = 3600  # 默认1小时刷新一次
            trace_id = TraceContext.generate_trace_id()
            cookie_logger = LoggerManager.get_logger(f"CookieRefresh.{cookie_id}")
            
            try:
                cookie_logger.info(f"开始定时刷新Cookie，间隔: {refresh_interval}秒")
                self.cookie_last_refresh[cookie_id] = time.time()
                
                while True:
                    await asyncio.sleep(refresh_interval)
                    try:
                        cookie_logger.info("开始执行Cookie刷新检查")
                        await self._refresh_cookie_if_needed(cookie_id, cookie_logger, trace_id)
                        self.cookie_last_refresh[cookie_id] = time.time()
                        cookie_logger.info("Cookie刷新检查完成")
                    except Exception as e:
                        cookie_logger.error(f"Cookie刷新过程中发生异常: {e}")
                        # 继续下一次刷新，不中断任务
                        await asyncio.sleep(300)  # 异常后等待5分钟再重试
                        
            except asyncio.CancelledError:
                cookie_logger.info("Cookie刷新任务被取消")
            except Exception as e:
                cookie_logger.error(f"Cookie刷新任务发生未捕获异常: {e}")
                
        # 创建并启动刷新任务
        task = self.loop.create_task(refresh_cookie_periodically())
        self.cookie_refresh_timers[cookie_id] = task
        self.logger.info(f"已启动Cookie {cookie_id} 的定时刷新任务")
        
    async def _refresh_cookie_if_needed(self, cookie_id: str, cookie_logger, trace_id: str):
        """检查并刷新Cookie（如果需要）"""
        try:
            cookie_logger.info(f"开始检查Cookie状态，追踪ID: {trace_id}")
            
            # 检查Cookie是否过期（这里需要根据实际业务逻辑实现）
            is_expired = await self._check_cookie_expiry(cookie_id)
            
            if is_expired:
                cookie_logger.warning(f"Cookie {cookie_id} 已过期，开始刷新")
                # 执行实际的Cookie刷新逻辑
                new_cookie = await self._perform_cookie_refresh(cookie_id)
                if new_cookie:
                    cookie_logger.info(f"Cookie {cookie_id} 刷新成功")
                    # 更新Cookie并重启任务
                    self.update_cookie(cookie_id, new_cookie)
                else:
                    cookie_logger.error(f"Cookie {cookie_id} 刷新失败")
            else:
                cookie_logger.info(f"Cookie {cookie_id} 状态正常，无需刷新")
                
        except Exception as e:
            cookie_logger.error(f"Cookie刷新检查过程中发生异常: {e}")
            raise
            
    async def _check_cookie_expiry(self, cookie_id: str) -> bool:
        """检查Cookie是否过期（需要根据实际业务实现）"""
        # 这里实现具体的Cookie过期检查逻辑
        # 可以检查最后使用时间、API调用结果等
        return False  # 默认不过期
        
    async def _perform_cookie_refresh(self, cookie_id: str) -> Optional[str]:
        """执行实际的Cookie刷新操作（需要根据实际业务实现）"""
        # 这里实现具体的Cookie刷新逻辑
        # 可以调用API、重新登录等方式获取新的Cookie
        try:
            self.logger.info(f"开始刷新Cookie: {cookie_id}")
            # 模拟刷新操作
            await asyncio.sleep(2)
            # 返回新的Cookie值（这里需要根据实际业务返回）
            return f"new_cookie_value_for_{cookie_id}_{int(time.time())}"
        except Exception as e:
            self.logger.error(f"Cookie刷新操作失败: {cookie_id}, {e}")
            return None
        
    def _stop_cookie_refresh_task(self, cookie_id: str):
        """停止单个Cookie的定时刷新任务"""
        if cookie_id in self.cookie_refresh_timers:
            task = self.cookie_refresh_timers.pop(cookie_id)
            if not task.done():
                task.cancel()
                self.logger.info(f"已停止Cookie {cookie_id} 的定时刷新任务")
        else:
            self.logger.warning(f"Cookie {cookie_id} 的刷新任务不存在，无需停止")
            
    def _start_cookie_task(self, cookie_id: str):
        """启动指定Cookie的任务"""
        if cookie_id in self.tasks:
            self.logger.warning(f"Cookie任务已存在，跳过启动: {cookie_id}")
            return

        cookie_value = self.cookies.get(cookie_id)
        if not cookie_value:
            self.logger.error(f"Cookie值不存在，无法启动任务: {cookie_id}")
            return

        try:
            # 获取Cookie对应的user_id
            cookie_info = db_manager.get_cookie_details(cookie_id)
            user_id = cookie_info.get('user_id') if cookie_info else None

            # 使用异步方式启动任务
            if hasattr(self.loop, 'is_running') and self.loop.is_running():
                # 事件循环正在运行，使用run_coroutine_threadsafe
                fut = asyncio.run_coroutine_threadsafe(
                    self._add_cookie_async(cookie_id, cookie_value, user_id),
                    self.loop
                )
                fut.result(timeout=5)  # 等待最多5秒
            else:
                # 事件循环未运行，直接创建任务
                task = self.loop.create_task(self._run_xianyu(cookie_id, cookie_value, user_id))
                self.tasks[cookie_id] = task

            # 启动定时刷新任务
            self._start_cookie_refresh_task(cookie_id)
            self.logger.info(f"成功启动Cookie任务: {cookie_id}")
        except Exception as e:
            self.logger.error(f"启动Cookie任务失败: {cookie_id}, {e}")

    def _stop_cookie_task(self, cookie_id: str):
        """停止指定Cookie的任务"""
        if cookie_id not in self.tasks:
            self.logger.warning(f"Cookie任务不存在，跳过停止: {cookie_id}")
            return

        try:
            task = self.tasks[cookie_id]
            if not task.done():
                task.cancel()
                self.logger.info(f"已取消Cookie任务: {cookie_id}")
            del self.tasks[cookie_id]
            
            # 停止定时刷新任务
            self._stop_cookie_refresh_task(cookie_id)
            self.logger.info(f"成功停止Cookie任务: {cookie_id}")
        except Exception as e:
            self.logger.error(f"停止Cookie任务失败: {cookie_id}, {e}")
            
    def update_cookie_status(self, cookie_id: str, enabled: bool):
        """更新Cookie的启用/禁用状态"""
        if cookie_id not in self.cookies:
            raise ValueError(f"Cookie ID {cookie_id} 不存在")

        old_status = self.cookie_status.get(cookie_id, True)
        self.cookie_status[cookie_id] = enabled
        # 保存到数据库
        db_manager.save_cookie_status(cookie_id, enabled)
        self.logger.info(f"更新Cookie状态: {cookie_id} -> {'启用' if enabled else '禁用'}")

        # 如果状态发生变化，需要启动或停止任务
        if old_status != enabled:
            if enabled:
                # 启用账号：启动任务
                self._start_cookie_task(cookie_id)
            else:
                # 禁用账号：停止任务
                self._stop_cookie_task(cookie_id)

    def _load_from_db(self):
        """从数据库加载所有Cookie、关键字和状态"""
        try:
            # 加载所有Cookie
            self.cookies = db_manager.get_all_cookies()
            # 加载所有关键字 - 为每个cookie单独加载
            self.keywords = {}
            for cookie_id in self.cookies.keys():
                self.keywords[cookie_id] = db_manager.get_keywords(cookie_id)
            # 加载所有Cookie状态（默认启用）
            self.cookie_status = {}
            # 加载所有auto_confirm设置
            self.auto_confirm_settings = {}
            for cookie_id in self.cookies.keys():
                # 为所有Cookie设置默认启用状态
                self.cookie_status[cookie_id] = True
                # 设置默认auto_confirm设置为False
                self.auto_confirm_settings[cookie_id] = False
            logger.info(f"从数据库加载了 {len(self.cookies)} 个Cookie、{len(self.keywords)} 组关键字、{len(self.cookie_status)} 个状态记录和 {len(self.auto_confirm_settings)} 个自动确认设置")
        except Exception as e:
            logger.error(f"从数据库加载数据失败: {e}")

    def reload_from_db(self):
        """重新从数据库加载所有数据（用于备份导入后刷新）"""
        logger.info("重新从数据库加载数据...")
        old_cookies_count = len(self.cookies)
        old_keywords_count = len(self.keywords)

        # 重新加载数据
        self._load_from_db()

        new_cookies_count = len(self.cookies)
        new_keywords_count = len(self.keywords)

        logger.info(f"数据重新加载完成: Cookie {old_cookies_count} -> {new_cookies_count}, 关键字组 {old_keywords_count} -> {new_keywords_count}")
        return True

    # ------------------------ 内部协程 ------------------------
    async def _run_xianyu(self, cookie_id: str, cookie_value: str, user_id: int = None):
        """在事件循环中启动 XianyuLive.main"""
        logger.info(f"【{cookie_id}】_run_xianyu方法开始执行...")

        try:
            logger.info(f"【{cookie_id}】正在导入XianyuLive...")
            from XianyuAutoAsync import XianyuLive  # 延迟导入，避免循环
            logger.info(f"【{cookie_id}】XianyuLive导入成功")

            logger.info(f"【{cookie_id}】开始创建XianyuLive实例...")
            logger.info(f"【{cookie_id}】Cookie值长度: {len(cookie_value)}")
            live = XianyuLive(cookie_value, cookie_id=cookie_id, user_id=user_id)
            logger.info(f"【{cookie_id}】XianyuLive实例创建成功，开始调用main()...")
            await live.main()
        except asyncio.CancelledError:
            logger.info(f"XianyuLive 任务已取消: {cookie_id}")
        except Exception as e:
            logger.error(f"XianyuLive 任务异常({cookie_id}): {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")

    async def _add_cookie_async(self, cookie_id: str, cookie_value: str, user_id: int = None):
        if cookie_id in self.tasks:
            raise ValueError("Cookie ID already exists")
        self.cookies[cookie_id] = cookie_value
        # 保存到数据库，如果没有指定user_id，则保持原有绑定关系
        db_manager.save_cookie(cookie_id, cookie_value, user_id)

        # 获取实际保存的user_id（如果没有指定，数据库会返回实际的user_id）
        actual_user_id = user_id
        if actual_user_id is None:
            # 从数据库获取Cookie对应的user_id
            cookie_info = db_manager.get_cookie_details(cookie_id)
            if cookie_info:
                actual_user_id = cookie_info.get('user_id')

        task = self.loop.create_task(self._run_xianyu(cookie_id, cookie_value, actual_user_id))
        self.tasks[cookie_id] = task
        logger.info(f"已启动账号任务: {cookie_id} (用户ID: {actual_user_id})")

    async def _remove_cookie_async(self, cookie_id: str):
        task = self.tasks.pop(cookie_id, None)
        if task:
            task.cancel()
        self.cookies.pop(cookie_id, None)
        self.keywords.pop(cookie_id, None)
        # 从数据库删除
        db_manager.delete_cookie(cookie_id)
        logger.info(f"已移除账号: {cookie_id}")

    # ------------------------ 对外线程安全接口 ------------------------
    def add_cookie(self, cookie_id: str, cookie_value: str, kw_list: Optional[List[Tuple[str, str]]] = None, user_id: int = None):
        """线程安全新增 Cookie 并启动任务"""
        if kw_list is not None:
            self.keywords[cookie_id] = kw_list
        else:
            self.keywords.setdefault(cookie_id, [])
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if current_loop and current_loop == self.loop:
            # 同一事件循环中，直接调度
            return self.loop.create_task(self._add_cookie_async(cookie_id, cookie_value, user_id))
        else:
            fut = asyncio.run_coroutine_threadsafe(self._add_cookie_async(cookie_id, cookie_value, user_id), self.loop)
            return fut.result()

    def remove_cookie(self, cookie_id: str):
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if current_loop and current_loop == self.loop:
            return self.loop.create_task(self._remove_cookie_async(cookie_id))
        else:
            fut = asyncio.run_coroutine_threadsafe(self._remove_cookie_async(cookie_id), self.loop)
            return fut.result()

    # 更新 Cookie 值
    def update_cookie(self, cookie_id: str, new_value: str):
        """替换指定账号的 Cookie 并重启任务"""
        async def _update():
            # 获取原有的user_id和关键词
            original_user_id = None
            original_keywords = []
            original_status = True

            cookie_info = db_manager.get_cookie_details(cookie_id)
            if cookie_info:
                original_user_id = cookie_info.get('user_id')

            # 保存原有的关键词和状态
            if cookie_id in self.keywords:
                original_keywords = self.keywords[cookie_id].copy()
            if cookie_id in self.cookie_status:
                original_status = self.cookie_status[cookie_id]

            # 先移除任务（但不删除数据库记录）
            task = self.tasks.pop(cookie_id, None)
            if task:
                task.cancel()

            # 更新Cookie值（保持原有user_id，不删除关键词）
            self.cookies[cookie_id] = new_value
            db_manager.save_cookie(cookie_id, new_value, original_user_id)

            # 恢复关键词和状态
            self.keywords[cookie_id] = original_keywords
            self.cookie_status[cookie_id] = original_status

            # 重新启动任务
            task = self.loop.create_task(self._run_xianyu(cookie_id, new_value, original_user_id))
            self.tasks[cookie_id] = task

            logger.info(f"已更新Cookie并重启任务: {cookie_id} (用户ID: {original_user_id}, 关键词: {len(original_keywords)}条)")

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if current_loop and current_loop == self.loop:
            return self.loop.create_task(_update())
        else:
            fut = asyncio.run_coroutine_threadsafe(_update(), self.loop)
            return fut.result()

    def update_keywords(self, cookie_id: str, kw_list: List[Tuple[str, str]]):
        """线程安全更新关键字"""
        self.keywords[cookie_id] = kw_list
        # 保存到数据库
        db_manager.save_keywords(cookie_id, kw_list)
        logger.info(f"更新关键字: {cookie_id} -> {len(kw_list)} 条")

    # 查询接口
    def list_cookies(self):
        return list(self.cookies.keys())

    def get_keywords(self, cookie_id: str) -> List[Tuple[str, str]]:
        return self.keywords.get(cookie_id, [])

    def update_cookie_status(self, cookie_id: str, enabled: bool):
        """更新Cookie的启用/禁用状态"""
        if cookie_id not in self.cookies:
            raise ValueError(f"Cookie ID {cookie_id} 不存在")

        old_status = self.cookie_status.get(cookie_id, True)
        self.cookie_status[cookie_id] = enabled
        # 保存到数据库
        db_manager.save_cookie_status(cookie_id, enabled)
        logger.info(f"更新Cookie状态: {cookie_id} -> {'启用' if enabled else '禁用'}")

        # 如果状态发生变化，需要启动或停止任务
        if old_status != enabled:
            if enabled:
                # 启用账号：启动任务
                self._start_cookie_task(cookie_id)
            else:
                # 禁用账号：停止任务
                self._stop_cookie_task(cookie_id)

    def get_cookie_status(self, cookie_id: str) -> bool:
        """获取Cookie的启用状态"""
        return self.cookie_status.get(cookie_id, True)  # 默认启用

    def get_enabled_cookies(self) -> Dict[str, str]:
        """获取所有启用的Cookie"""
        return {cid: value for cid, value in self.cookies.items()
                if self.cookie_status.get(cid, True)}

    def _start_cookie_task(self, cookie_id: str):
        """启动指定Cookie的任务"""
        if cookie_id in self.tasks:
            logger.warning(f"Cookie任务已存在，跳过启动: {cookie_id}")
            return

        cookie_value = self.cookies.get(cookie_id)
        if not cookie_value:
            logger.error(f"Cookie值不存在，无法启动任务: {cookie_id}")
            return

        try:
            # 获取Cookie对应的user_id
            cookie_info = db_manager.get_cookie_details(cookie_id)
            user_id = cookie_info.get('user_id') if cookie_info else None

            # 使用异步方式启动任务
            if hasattr(self.loop, 'is_running') and self.loop.is_running():
                # 事件循环正在运行，使用run_coroutine_threadsafe
                fut = asyncio.run_coroutine_threadsafe(
                    self._add_cookie_async(cookie_id, cookie_value, user_id),
                    self.loop
                )
                fut.result(timeout=5)  # 等待最多5秒
            else:
                # 事件循环未运行，直接创建任务
                task = self.loop.create_task(self._run_xianyu(cookie_id, cookie_value, user_id))
                self.tasks[cookie_id] = task

            logger.info(f"成功启动Cookie任务: {cookie_id}")
        except Exception as e:
            logger.error(f"启动Cookie任务失败: {cookie_id}, {e}")

    def _stop_cookie_task(self, cookie_id: str):
        """停止指定Cookie的任务"""
        if cookie_id not in self.tasks:
            logger.warning(f"Cookie任务不存在，跳过停止: {cookie_id}")
            return

        try:
            task = self.tasks[cookie_id]
            if not task.done():
                task.cancel()
                logger.info(f"已取消Cookie任务: {cookie_id}")
            del self.tasks[cookie_id]
            logger.info(f"成功停止Cookie任务: {cookie_id}")
        except Exception as e:
            logger.error(f"停止Cookie任务失败: {cookie_id}, {e}")

    def update_auto_confirm_setting(self, cookie_id: str, auto_confirm: bool):
        """实时更新账号的自动确认发货设置"""
        try:
            # 更新内存中的设置
            self.auto_confirm_settings[cookie_id] = auto_confirm
            logger.info(f"更新账号 {cookie_id} 自动确认发货设置: {'开启' if auto_confirm else '关闭'}")

            # 如果账号正在运行，通知XianyuLive实例更新设置
            if cookie_id in self.tasks and not self.tasks[cookie_id].done():
                # 这里可以通过某种方式通知正在运行的XianyuLive实例
                # 由于XianyuLive会从数据库读取设置，所以数据库已经更新就足够了
                logger.info(f"账号 {cookie_id} 正在运行，自动确认发货设置已实时生效")
        except Exception as e:
            logger.error(f"更新自动确认发货设置失败: {cookie_id}, {e}")

    def get_auto_confirm_setting(self, cookie_id: str) -> bool:
        """获取账号的自动确认发货设置"""
        return self.auto_confirm_settings.get(cookie_id, True)  # 默认开启

    def _init_auto_updater(self):
        """初始化Cookie自动更新器"""
        try:
            # 为所有启用的Cookie启动自动更新
            for cookie_id, cookie_value in self.cookies.items():
                if self.cookie_status.get(cookie_id, True):  # 默认启用
                    device_id = f"device_{cookie_id}"
                    # 启动自动更新任务
                    cookie_auto_updater.start_account_auto_update(cookie_id, cookie_value, device_id)
                    self.auto_update_enabled[cookie_id] = True
                    self.logger.info(f"为账号 {cookie_id} 启动Cookie自动更新")
            
            self.logger.info(f"Cookie自动更新器初始化完成，已启动 {len([k for k, v in self.auto_update_enabled.items() if v])} 个账号的自动更新")
        except Exception as e:
            self.logger.error(f"初始化Cookie自动更新器失败: {e}")
    
    def _init_token_manager(self):
        """初始化Token管理器"""
        try:
            # 启动Token管理器
            asyncio.create_task(self._start_token_manager())
            self.logger.info("Token管理器初始化完成")
        except Exception as e:
            self.logger.error(f"初始化Token管理器失败: {e}")
    
    async def _start_token_manager(self):
        """启动Token管理器"""
        try:
            # 启动Token管理器
            await token_manager.start()
            
            # 为所有启用的Cookie添加到Token管理
            for cookie_id, cookie_value in self.cookies.items():
                if self.cookie_status.get(cookie_id, True):  # 默认启用
                    device_id = f"device_{cookie_id}"
                    success = await token_manager.add_account(cookie_id, cookie_value, device_id)
                    if success:
                        self.logger.info(f"账号 {cookie_id} 已添加到Token管理")
                    else:
                        self.logger.warning(f"账号 {cookie_id} 添加到Token管理失败")
            
            self.logger.info(f"Token管理器启动完成，已管理 {len(token_manager.tokens)} 个账号")
        except Exception as e:
            self.logger.error(f"启动Token管理器失败: {e}")

    # ======================== Cookie自动更新相关方法 ========================
    
    def enable_cookie_auto_update(self, cookie_id: str) -> bool:
        """启用指定账号的Cookie自动更新"""
        try:
            if cookie_id not in self.cookies:
                self.logger.error(f"账号 {cookie_id} 不存在，无法启用自动更新")
                return False
            
            if self.auto_update_enabled.get(cookie_id, False):
                self.logger.info(f"账号 {cookie_id} 的Cookie自动更新已经启用")
                return True
            
            cookie_value = self.cookies[cookie_id]
            device_id = f"device_{cookie_id}"
            
            # 启动自动更新任务
            cookie_auto_updater.start_account_auto_update(cookie_id, cookie_value, device_id)
            self.auto_update_enabled[cookie_id] = True
            
            self.logger.info(f"已启用账号 {cookie_id} 的Cookie自动更新")
            return True
            
        except Exception as e:
            self.logger.error(f"启用账号 {cookie_id} Cookie自动更新失败: {e}")
            return False
    
    def disable_cookie_auto_update(self, cookie_id: str) -> bool:
        """禁用指定账号的Cookie自动更新"""
        try:
            if cookie_id not in self.cookies:
                self.logger.error(f"账号 {cookie_id} 不存在，无法禁用自动更新")
                return False
            
            if not self.auto_update_enabled.get(cookie_id, False):
                self.logger.info(f"账号 {cookie_id} 的Cookie自动更新已经禁用")
                return True
            
            # 停止自动更新任务
            cookie_auto_updater.stop_account_auto_update(cookie_id)
            self.auto_update_enabled[cookie_id] = False
            
            self.logger.info(f"已禁用账号 {cookie_id} 的Cookie自动更新")
            return True
            
        except Exception as e:
            self.logger.error(f"禁用账号 {cookie_id} Cookie自动更新失败: {e}")
            return False
    
    def is_cookie_auto_update_enabled(self, cookie_id: str) -> bool:
        """检查指定账号的Cookie自动更新是否启用"""
        return self.auto_update_enabled.get(cookie_id, False)
    
    async def force_update_cookie(self, cookie_id: str) -> bool:
        """强制更新指定账号的Cookie"""
        try:
            if cookie_id not in self.cookies:
                self.logger.error(f"账号 {cookie_id} 不存在，无法强制更新Cookie")
                return False
            
            self.logger.info(f"开始强制更新账号 {cookie_id} 的Cookie...")
            
            # 调用自动更新器的强制更新方法
            success = await cookie_auto_updater.force_update_account(cookie_id)
            
            if success:
                self.logger.info(f"账号 {cookie_id} Cookie强制更新成功")
                return True
            else:
                self.logger.error(f"账号 {cookie_id} Cookie强制更新失败")
                return False
                
        except Exception as e:
            self.logger.error(f"强制更新账号 {cookie_id} Cookie异常: {e}")
            return False
    
    def force_update_cookie_sync(self, cookie_id: str) -> bool:
        """同步方式强制更新指定账号的Cookie"""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if current_loop and current_loop == self.loop:
            # 在同一事件循环中，创建任务
            task = self.loop.create_task(self.force_update_cookie(cookie_id))
            return task
        else:
            # 在不同线程中，使用run_coroutine_threadsafe
            fut = asyncio.run_coroutine_threadsafe(self.force_update_cookie(cookie_id), self.loop)
            return fut.result(timeout=30)  # 30秒超时
    
    async def batch_update_cookies(self, cookie_ids: List[str] = None) -> Dict[str, bool]:
        """批量更新多个账号的Cookie"""
        try:
            if cookie_ids is None:
                # 更新所有启用的账号
                cookie_ids = [cid for cid, enabled in self.cookie_status.items() if enabled]
            
            self.logger.info(f"开始批量更新 {len(cookie_ids)} 个账号的Cookie...")
            
            # 准备账号信息
            cookie_accounts = {}
            for cookie_id in cookie_ids:
                if cookie_id in self.cookies:
                    cookie_accounts[cookie_id] = {
                        'cookie_value': self.cookies[cookie_id],
                        'device_id': f"device_{cookie_id}"
                    }
            
            # 调用自动更新器的批量更新方法
            updated_cookies = await cookie_auto_updater.batch_update_cookies(cookie_accounts)
            
            # 处理更新结果
            results = {}
            for cookie_id in cookie_ids:
                if cookie_id in updated_cookies:
                    results[cookie_id] = True
                    self.logger.info(f"账号 {cookie_id} Cookie批量更新成功")
                else:
                    results[cookie_id] = False
                    self.logger.warning(f"账号 {cookie_id} Cookie批量更新失败")
            
            success_count = sum(results.values())
            self.logger.info(f"批量更新完成，成功: {success_count}/{len(cookie_ids)}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"批量更新Cookie异常: {e}")
            return {cookie_id: False for cookie_id in (cookie_ids or [])}
    
    def get_cookie_token(self, cookie_id: str) -> Optional[str]:
        """获取指定账号的缓存Token"""
        return cookie_auto_updater.get_account_token(cookie_id)
    
    def is_cookie_token_valid(self, cookie_id: str) -> bool:
        """检查指定账号的Token是否有效"""
        return cookie_auto_updater.is_token_valid(cookie_id)
    
    def get_cookie_auto_update_status(self) -> Dict[str, Dict[str, any]]:
        """获取所有账号的Cookie自动更新状态"""
        status = {}
        for cookie_id in self.cookies.keys():
            status[cookie_id] = {
                'auto_update_enabled': self.auto_update_enabled.get(cookie_id, False),
                'token_valid': self.is_cookie_token_valid(cookie_id),
                'has_token': self.get_cookie_token(cookie_id) is not None,
                'account_enabled': self.cookie_status.get(cookie_id, True),
                # 添加Token管理器状态
                'token_manager_valid': token_manager.is_token_valid(cookie_id),
                'token_manager_token': token_manager.get_token(cookie_id) is not None
            }
        return status
    
    # ======================== Token管理器集成方法 ========================
    
    async def add_account_to_token_manager(self, cookie_id: str) -> bool:
        """将账号添加到Token管理器"""
        try:
            if cookie_id not in self.cookies:
                self.logger.error(f"账号 {cookie_id} 不存在，无法添加到Token管理器")
                return False
            
            cookie_value = self.cookies[cookie_id]
            device_id = f"device_{cookie_id}"
            
            success = await token_manager.add_account(cookie_id, cookie_value, device_id)
            if success:
                self.logger.info(f"账号 {cookie_id} 已成功添加到Token管理器")
            else:
                self.logger.error(f"账号 {cookie_id} 添加到Token管理器失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"添加账号 {cookie_id} 到Token管理器异常: {e}")
            return False
    
    async def remove_account_from_token_manager(self, cookie_id: str):
        """从Token管理器中移除账号"""
        try:
            await token_manager.remove_account(cookie_id)
            self.logger.info(f"账号 {cookie_id} 已从Token管理器中移除")
        except Exception as e:
            self.logger.error(f"从Token管理器移除账号 {cookie_id} 异常: {e}")
    
    def get_token_manager_status(self) -> Dict[str, dict]:
        """获取Token管理器状态"""
        return token_manager.get_all_tokens_status()
    
    async def force_refresh_account_token(self, cookie_id: str) -> bool:
        """强制刷新指定账号的Token"""
        try:
            success = await token_manager.force_refresh_token(cookie_id)
            if success:
                self.logger.info(f"账号 {cookie_id} Token强制刷新成功")
            else:
                self.logger.error(f"账号 {cookie_id} Token强制刷新失败")
            return success
        except Exception as e:
            self.logger.error(f"强制刷新账号 {cookie_id} Token异常: {e}")
            return False
    
    def force_refresh_account_token_sync(self, cookie_id: str) -> bool:
        """同步方式强制刷新指定账号的Token"""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if current_loop and current_loop == self.loop:
            # 在同一事件循环中，创建任务
            task = self.loop.create_task(self.force_refresh_account_token(cookie_id))
            return task
        else:
            # 在不同线程中，使用run_coroutine_threadsafe
            fut = asyncio.run_coroutine_threadsafe(self.force_refresh_account_token(cookie_id), self.loop)
            return fut.result(timeout=30)  # 30秒超时
    
    async def batch_refresh_tokens(self, cookie_ids: List[str] = None) -> Dict[str, bool]:
        """批量刷新Token"""
        try:
            if cookie_ids is None:
                # 刷新所有启用的账号
                cookie_ids = [cid for cid, enabled in self.cookie_status.items() if enabled]
            
            results = await token_manager.batch_refresh_tokens(cookie_ids)
            
            success_count = sum(results.values())
            self.logger.info(f"批量Token刷新完成，成功: {success_count}/{len(cookie_ids)}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"批量刷新Token异常: {e}")
            return {cookie_id: False for cookie_id in (cookie_ids or [])}
    
    def get_account_token(self, cookie_id: str) -> Optional[str]:
        """获取指定账号的Token"""
        return token_manager.get_token(cookie_id)
    
    def is_account_token_valid(self, cookie_id: str) -> bool:
        """检查指定账号的Token是否有效"""
        return token_manager.is_token_valid(cookie_id)
    
    def get_account_token_info(self, cookie_id: str) -> Optional[dict]:
        """获取指定账号的Token详细信息"""
        token_info = token_manager.get_token_info(cookie_id)
        return token_info.to_dict() if token_info else None


# 在 Start.py 中会把此变量赋值为具体实例
manager: Optional[CookieManager] = None 