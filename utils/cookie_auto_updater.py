"""
Cookie自动更新器 - 移植自XianyuAutoAgent-main项目并适配xianyu-auto-reply

核心功能：
1. 自动检测Cookie失效
2. 通过hasLogin接口重新登录
3. 自动更新Token
4. 清理重复Cookie
5. 实时更新配置文件
6. 支持多账号并发更新
"""

import time
import os
import asyncio
import requests
from typing import Dict, Optional, List
from loguru import logger
from db_manager import db_manager
from utils.xianyu_utils import generate_sign
from config import Config


class CookieAutoUpdater:
    """Cookie自动更新器"""
    
    def __init__(self):
        self.session = requests.Session()
        self._setup_headers()
        
        # 加载配置
        self.config = Config()
        
        # Token刷新配置 - 优先从配置文件获取，其次环境变量，最后默认值
        cookie_config = self.config.get('COOKIE_AUTO_UPDATE', {})
        self.enabled = cookie_config.get('enabled', True)
        self.token_refresh_interval = cookie_config.get('refresh_interval', 
                                                       int(os.getenv("TOKEN_REFRESH_INTERVAL", "3600")))
        self.token_retry_interval = cookie_config.get('retry_interval',
                                                     int(os.getenv("TOKEN_RETRY_INTERVAL", "300")))
        self.batch_size = cookie_config.get('batch_size', 5)
        self.timeout = cookie_config.get('timeout', 30)
        self.auto_start = cookie_config.get('auto_start', True)
        
        # 账号Token缓存
        self.account_tokens: Dict[str, str] = {}
        self.account_token_timestamps: Dict[str, float] = {}
        
        # 更新任务管理
        self.update_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info(f"Cookie自动更新器初始化完成 - 启用状态: {self.enabled}, 刷新间隔: {self.token_refresh_interval}秒")
        
    def _setup_headers(self):
        """设置HTTP请求头"""
        self.session.headers.update({
            'accept': 'application/json',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cache-control': 'no-cache',
            'origin': 'https://www.goofish.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://www.goofish.com/',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        })
    
    def parse_cookie_string(self, cookie_str: str) -> Dict[str, str]:
        """解析Cookie字符串为字典"""
        cookies = {}
        if not cookie_str:
            return cookies
            
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        return cookies
    
    def dict_to_cookie_string(self, cookies_dict: Dict[str, str]) -> str:
        """将Cookie字典转换为字符串"""
        return '; '.join([f"{k}={v}" for k, v in cookies_dict.items()])
    
    def clear_duplicate_cookies(self, cookie_str: str) -> str:
        """清理重复的Cookie"""
        try:
            # 解析Cookie字符串
            cookies_dict = self.parse_cookie_string(cookie_str)
            
            # 重新组合，自动去重
            cleaned_cookie_str = self.dict_to_cookie_string(cookies_dict)
            
            logger.debug(f"Cookie清理完成，原长度: {len(cookie_str)}, 新长度: {len(cleaned_cookie_str)}")
            return cleaned_cookie_str
            
        except Exception as e:
            logger.error(f"清理Cookie失败: {e}")
            return cookie_str
    
    def update_session_cookies(self, cookie_str: str):
        """更新Session的Cookie"""
        try:
            # 清空现有Cookie
            self.session.cookies.clear()
            
            # 解析并设置新Cookie
            cookies_dict = self.parse_cookie_string(cookie_str)
            for name, value in cookies_dict.items():
                self.session.cookies.set(name, value)
                
            logger.debug("Session Cookie更新完成")
            
        except Exception as e:
            logger.error(f"更新Session Cookie失败: {e}")
    
    async def has_login(self, cookie_str: str, retry_count: int = 0) -> bool:
        """检查登录状态并尝试重新登录"""
        if retry_count >= 2:
            logger.error("登录检查失败，重试次数过多")
            return False
            
        try:
            # 更新Session Cookie
            self.update_session_cookies(cookie_str)
            
            url = 'https://passport.goofish.com/newlogin/hasLogin.do'
            params = {
                'appName': 'xianyu',
                'fromSite': '77'
            }
            
            cookies_dict = self.parse_cookie_string(cookie_str)
            data = {
                'hid': cookies_dict.get('unb', ''),
                'ltl': 'true',
                'appName': 'xianyu',
                'appEntrance': 'web',
                '_csrf_token': cookies_dict.get('XSRF-TOKEN', ''),
                'umidToken': '',
                'hsiz': cookies_dict.get('cookie2', ''),
                'bizParams': 'taobaoBizLoginFrom=web',
                'mainPage': 'false',
                'isMobile': 'false',
                'lang': 'zh_CN',
                'returnUrl': '',
                'fromSite': '77',
                'isIframe': 'true',
                'documentReferer': 'https://www.goofish.com/',
                'defaultView': 'hasLogin',
                'umidTag': 'SERVER',
                'deviceId': cookies_dict.get('cna', '')
            }
            
            response = self.session.post(url, params=params, data=data)
            res_json = response.json()
            
            if res_json.get('content', {}).get('success'):
                logger.info("登录状态检查成功")
                
                # 处理响应中的新Cookie
                if 'Set-Cookie' in response.headers:
                    logger.debug("检测到新Cookie，准备更新")
                    # 获取更新后的Cookie
                    updated_cookie_str = self.dict_to_cookie_string(
                        {cookie.name: cookie.value for cookie in self.session.cookies}
                    )
                    return updated_cookie_str
                
                return cookie_str  # 返回原Cookie
            else:
                logger.warning(f"登录状态检查失败: {res_json}")
                await asyncio.sleep(0.5)
                return await self.has_login(cookie_str, retry_count + 1)
                
        except Exception as e:
            logger.error(f"登录状态检查异常: {str(e)}")
            await asyncio.sleep(0.5)
            return await self.has_login(cookie_str, retry_count + 1)
    
    async def get_token(self, cookie_str: str, device_id: str, retry_count: int = 0) -> Optional[str]:
        """获取访问Token"""
        if retry_count >= 2:
            logger.warning("获取Token失败，尝试重新登录")
            # 尝试重新登录
            updated_cookie = await self.has_login(cookie_str)
            if updated_cookie and updated_cookie != cookie_str:
                logger.info("重新登录成功，重新尝试获取Token")
                return await self.get_token(updated_cookie, device_id, 0)
            else:
                logger.error("重新登录失败，Cookie已失效")
                return None
        
        try:
            # 更新Session Cookie
            self.update_session_cookies(cookie_str)
            
            params = {
                'jsv': '2.7.2',
                'appKey': '34839810',
                't': str(int(time.time()) * 1000),
                'sign': '',
                'v': '1.0',
                'type': 'originaljson',
                'accountSite': 'xianyu',
                'dataType': 'json',
                'timeout': '20000',
                'api': 'mtop.taobao.idlemessage.pc.login.token',
                'sessionOption': 'AutoLoginOnly',
                'spm_cnt': 'a21ybx.im.0.0',
            }
            
            data_val = f'{{"appKey":"444e9908a51d1cb236a27862abc769c9","deviceId":"{device_id}"}}'
            data = {'data': data_val}
            
            # 获取Token用于签名
            cookies_dict = self.parse_cookie_string(cookie_str)
            token = cookies_dict.get('_m_h5_tk', '').split('_')[0]
            
            sign = generate_sign(params['t'], token, data_val)
            params['sign'] = sign
            
            response = self.session.post(
                'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/',
                params=params,
                data=data
            )
            
            res_json = response.json()
            
            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                    logger.warning(f"Token API调用失败，错误信息: {ret_value}")
                    
                    # 检查是否是系统过载或验证失败
                    error_str = str(ret_value)
                    if 'FAIL_SYS_USER_VALIDATE' in error_str or '被挤爆啦' in error_str:
                        if retry_count >= 2:  # 限制重试次数
                            logger.error(f"Token获取失败次数过多，停止重试: {ret_value}")
                            return None
                        
                        # 使用指数退避策略
                        wait_time = min(2 ** retry_count, 10)  # 最多等待10秒
                        logger.info(f"系统繁忙，等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                        return None  # 直接返回，避免无限重试
                    
                    # 处理响应中的Set-Cookie
                    if 'Set-Cookie' in response.headers:
                        logger.debug("检测到Set-Cookie，更新Cookie")
                        updated_cookie_str = self.dict_to_cookie_string(
                            {cookie.name: cookie.value for cookie in self.session.cookies}
                        )
                        # 递归调用，使用更新后的Cookie
                        return await self.get_token(updated_cookie_str, device_id, retry_count + 1)
                    
                    await asyncio.sleep(0.5)
                    return await self.get_token(cookie_str, device_id, retry_count + 1)
                else:
                    logger.info("Token获取成功")
                    # 返回Token和可能更新的Cookie
                    access_token = res_json.get('data', {}).get('accessToken')
                    if access_token:
                        return {
                            'token': access_token,
                            'cookie': self.dict_to_cookie_string(
                                {cookie.name: cookie.value for cookie in self.session.cookies}
                            )
                        }
                    return None
            else:
                logger.error(f"Token API返回格式异常: {res_json}")
                return await self.get_token(cookie_str, device_id, retry_count + 1)
                
        except Exception as e:
            logger.error(f"Token API请求异常: {str(e)}")
            await asyncio.sleep(0.5)
            return await self.get_token(cookie_str, device_id, retry_count + 1)
    
    async def update_account_cookie(self, cookie_id: str, cookie_value: str, device_id: str) -> Optional[str]:
        """更新单个账号的Cookie"""
        try:
            logger.info(f"开始更新账号Cookie: {cookie_id}")
            
            # 0. 验证Cookie格式
            from utils.xianyu_utils import trans_cookies
            cookie_dict = trans_cookies(cookie_value)
            if not cookie_dict:
                logger.error(f"账号 {cookie_id} Cookie格式无效，跳过自动更新")
                return None
            
            if 'unb' not in cookie_dict:
                logger.error(f"账号 {cookie_id} Cookie缺少必需的'unb'字段，跳过自动更新")
                return None
            
            # 1. 清理重复Cookie
            cleaned_cookie = self.clear_duplicate_cookies(cookie_value)
            
            # 2. 检查登录状态
            login_result = await self.has_login(cleaned_cookie)
            if isinstance(login_result, str):
                cleaned_cookie = login_result
            elif not login_result:
                logger.error(f"账号 {cookie_id} 登录状态检查失败")
                return None
            
            # 3. 获取新Token
            token_result = await self.get_token(cleaned_cookie, device_id)
            if token_result and isinstance(token_result, dict):
                new_token = token_result['token']
                updated_cookie = token_result['cookie']
                
                # 4. 缓存Token
                self.account_tokens[cookie_id] = new_token
                self.account_token_timestamps[cookie_id] = time.time()
                
                # 5. 更新数据库
                db_manager.save_cookie(cookie_id, updated_cookie)
                
                logger.info(f"账号 {cookie_id} Cookie更新成功")
                return updated_cookie
            else:
                logger.error(f"账号 {cookie_id} Token获取失败")
                return None
                
        except Exception as e:
            logger.error(f"更新账号 {cookie_id} Cookie失败: {e}")
            return None
    
    async def batch_update_cookies(self, cookie_accounts: Dict[str, Dict]) -> Dict[str, str]:
        """批量更新多个账号的Cookie"""
        logger.info(f"开始批量更新 {len(cookie_accounts)} 个账号的Cookie")
        
        # 创建并发任务
        tasks = []
        for cookie_id, account_info in cookie_accounts.items():
            cookie_value = account_info['cookie_value']
            device_id = account_info.get('device_id', f"device_{cookie_id}")
            
            task = asyncio.create_task(
                self.update_account_cookie(cookie_id, cookie_value, device_id)
            )
            tasks.append((cookie_id, task))
        
        # 等待所有任务完成
        results = {}
        for cookie_id, task in tasks:
            try:
                updated_cookie = await task
                if updated_cookie:
                    results[cookie_id] = updated_cookie
                else:
                    logger.warning(f"账号 {cookie_id} Cookie更新失败")
            except Exception as e:
                logger.error(f"账号 {cookie_id} 更新任务异常: {e}")
        
        logger.info(f"批量更新完成，成功更新 {len(results)} 个账号")
        return results
    
    async def start_auto_update_loop(self, cookie_id: str, cookie_value: str, device_id: str):
        """启动单个账号的自动更新循环"""
        logger.info(f"启动账号 {cookie_id} 的自动更新循环")
        
        while True:
            try:
                current_time = time.time()
                last_update_time = self.account_token_timestamps.get(cookie_id, 0)
                
                # 检查是否需要更新
                if current_time - last_update_time >= self.token_refresh_interval:
                    logger.info(f"账号 {cookie_id} Token即将过期，准备更新...")
                    
                    updated_cookie = await self.update_account_cookie(cookie_id, cookie_value, device_id)
                    if updated_cookie:
                        # 通知Cookie管理器更新 - 适配xianyu-auto-reply项目
                        try:
                            import cookie_manager
                            if hasattr(cookie_manager, 'manager') and cookie_manager.manager:
                                cookie_manager.manager.update_cookie(cookie_id, updated_cookie)
                                logger.info(f"已通知cookie_manager更新账号 {cookie_id}")
                        except Exception as e:
                            logger.warning(f"通知cookie_manager更新失败: {e}")
                        
                        logger.info(f"账号 {cookie_id} 自动更新成功")
                    else:
                        logger.error(f"账号 {cookie_id} 自动更新失败，将在 {self.token_retry_interval // 60} 分钟后重试")
                        await asyncio.sleep(self.token_retry_interval)
                        continue
                
                # 每分钟检查一次
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info(f"账号 {cookie_id} 自动更新循环已取消")
                break
            except Exception as e:
                logger.error(f"账号 {cookie_id} 自动更新循环异常: {e}")
                await asyncio.sleep(60)
    
    def start_account_auto_update(self, cookie_id: str, cookie_value: str, device_id: str):
        """启动账号的自动更新任务"""
        # 检查是否启用自动更新功能
        if not self.enabled:
            logger.info(f"Cookie自动更新功能已禁用，跳过启动账号 {cookie_id}")
            return
            
        # 取消现有任务
        if cookie_id in self.update_tasks:
            self.update_tasks[cookie_id].cancel()
        
        # 创建新任务
        task = asyncio.create_task(
            self.start_auto_update_loop(cookie_id, cookie_value, device_id)
        )
        self.update_tasks[cookie_id] = task
        
        logger.info(f"账号 {cookie_id} 自动更新任务已启动")
    
    def stop_account_auto_update(self, cookie_id: str):
        """停止账号的自动更新任务"""
        if cookie_id in self.update_tasks:
            self.update_tasks[cookie_id].cancel()
            del self.update_tasks[cookie_id]
            logger.info(f"账号 {cookie_id} 自动更新任务已停止")
    
    def get_account_token(self, cookie_id: str) -> Optional[str]:
        """获取账号的缓存Token"""
        return self.account_tokens.get(cookie_id)
    
    def is_token_valid(self, cookie_id: str) -> bool:
        """检查账号Token是否有效"""
        if cookie_id not in self.account_token_timestamps:
            return False
        
        current_time = time.time()
        last_update_time = self.account_token_timestamps[cookie_id]
        
        return (current_time - last_update_time) < self.token_refresh_interval
    
    async def force_update_account(self, cookie_id: str) -> bool:
        """强制更新指定账号的Cookie"""
        try:
            # 从数据库获取账号信息
            cookie_info = db_manager.get_cookie_details(cookie_id)
            if not cookie_info:
                logger.error(f"账号 {cookie_id} 不存在")
                return False
            
            cookie_value = cookie_info['cookie_value']
            device_id = cookie_info.get('device_id', f"device_{cookie_id}")
            
            updated_cookie = await self.update_account_cookie(cookie_id, cookie_value, device_id)
            if updated_cookie:
                # 通知Cookie管理器更新 - 适配xianyu-auto-reply项目
                try:
                    import cookie_manager
                    if hasattr(cookie_manager, 'manager') and cookie_manager.manager:
                        cookie_manager.manager.update_cookie(cookie_id, updated_cookie)
                        logger.info(f"已通知cookie_manager更新账号 {cookie_id}")
                except Exception as e:
                    logger.warning(f"通知cookie_manager更新失败: {e}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"强制更新账号 {cookie_id} 失败: {e}")
            return False


# 全局实例 - 适配xianyu-auto-reply项目结构
cookie_auto_updater = CookieAutoUpdater()