"""
Token管理器 - 集成XianyuAutoAgent的Token刷新策略
基于XianyuAutoAgent项目的长连接Cookie刷新功能
"""

import asyncio
import time
import json
import hashlib
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, asdict
from loguru import logger
import requests
from utils.xianyu_utils import generate_sign


@dataclass
class TokenInfo:
    """Token信息数据类"""
    token: str
    device_id: str
    cookie_value: str
    last_refresh_time: float
    expires_at: float
    refresh_count: int = 0
    is_valid: bool = True
    error_count: int = 0
    
    def is_expired(self) -> bool:
        """检查Token是否过期"""
        return time.time() >= self.expires_at
    
    def needs_refresh(self, refresh_interval: int = 3600) -> bool:
        """检查是否需要刷新"""
        return (time.time() - self.last_refresh_time) >= refresh_interval
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


class XianyuTokenManager:
    """闲鱼Token管理器 - 集成XianyuAutoAgent的策略"""
    
    def __init__(self):
        self.tokens: Dict[str, TokenInfo] = {}
        self.refresh_tasks: Dict[str, asyncio.Task] = {}
        self.session_pool: Dict[str, requests.Session] = {}
        self.is_running = False
        
        # 配置参数
        self.default_refresh_interval = 3600  # 1小时
        self.token_expire_time = 7200  # 2小时过期
        self.max_error_count = 3
        self.retry_delay = 300  # 5分钟重试延迟
        
        logger.info("XianyuTokenManager初始化完成")
    
    def _create_session(self, cookie_id: str) -> requests.Session:
        """为指定账号创建HTTP会话"""
        if cookie_id in self.session_pool:
            return self.session_pool[cookie_id]
            
        session = requests.Session()
        session.headers.update({
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
        
        self.session_pool[cookie_id] = session
        return session
    
    def _parse_cookie_string(self, cookie_string: str) -> Dict[str, str]:
        """解析Cookie字符串"""
        cookies = {}
        for item in cookie_string.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies[key] = value
        return cookies
    
    def _update_session_cookies(self, session: requests.Session, cookie_string: str):
        """更新会话的Cookie"""
        cookies = self._parse_cookie_string(cookie_string)
        for name, value in cookies.items():
            session.cookies.set(name, value)
    
    def _clear_duplicate_cookies(self, session: requests.Session):
        """清理重复的cookies - 基于XianyuAutoAgent的实现"""
        new_jar = requests.cookies.RequestsCookieJar()
        added_cookies = set()
        
        cookie_list = list(session.cookies)
        cookie_list.reverse()
        
        for cookie in cookie_list:
            if cookie.name not in added_cookies:
                new_jar.set_cookie(cookie)
                added_cookies.add(cookie.name)
                
        session.cookies = new_jar
    
    async def _check_login_status(self, cookie_id: str, session: requests.Session) -> bool:
        """检查登录状态 - 基于XianyuAutoAgent的hasLogin实现"""
        try:
            url = 'https://passport.goofish.com/newlogin/hasLogin.do'
            params = {
                'appName': 'xianyu',
                'fromSite': '77'
            }
            data = {
                'hid': session.cookies.get('unb', ''),
                'ltl': 'true',
                'appName': 'xianyu',
                'appEntrance': 'web',
                '_csrf_token': session.cookies.get('XSRF-TOKEN', ''),
                'umidToken': '',
                'hsiz': session.cookies.get('cookie2', ''),
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
                'deviceId': session.cookies.get('cna', '')
            }
            
            response = session.post(url, params=params, data=data)
            res_json = response.json()
            
            if res_json.get('content', {}).get('success'):
                logger.debug(f"账号 {cookie_id} 登录状态检查成功")
                self._clear_duplicate_cookies(session)
                return True
            else:
                logger.warning(f"账号 {cookie_id} 登录状态检查失败: {res_json}")
                return False
                
        except Exception as e:
            logger.error(f"账号 {cookie_id} 登录状态检查异常: {e}")
            return False
    
    async def _refresh_token(self, cookie_id: str, device_id: str, session: requests.Session) -> Optional[str]:
        """刷新Token - 基于XianyuAutoAgent的get_token实现"""
        try:
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
            
            data_val = json.dumps({"appKey": "444e9908a51d1cb236a27862abc769c9", "deviceId": device_id})
            data = {'data': data_val}
            
            # 获取当前token
            current_token = session.cookies.get('_m_h5_tk', '').split('_')[0]
            
            # 生成签名
            sign = generate_sign(params['t'], current_token, data_val)
            params['sign'] = sign
            
            response = session.post(
                'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/',
                params=params,
                data=data
            )
            
            res_json = response.json()
            
            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                if any('SUCCESS::调用成功' in ret for ret in ret_value):
                    logger.info(f"账号 {cookie_id} Token刷新成功")
                    
                    # 处理响应中的Set-Cookie
                    if 'Set-Cookie' in response.headers:
                        self._clear_duplicate_cookies(session)
                    
                    # 获取新的token
                    new_token = session.cookies.get('_m_h5_tk', '').split('_')[0]
                    return new_token
                else:
                    logger.warning(f"账号 {cookie_id} Token刷新失败: {ret_value}")
                    return None
            else:
                logger.error(f"账号 {cookie_id} Token API返回格式异常: {res_json}")
                return None
                
        except Exception as e:
            logger.error(f"账号 {cookie_id} Token刷新异常: {e}")
            return None
    
    async def add_account(self, cookie_id: str, cookie_value: str, device_id: str = None) -> bool:
        """添加账号到Token管理"""
        try:
            if device_id is None:
                device_id = f"device_{cookie_id}_{int(time.time())}"
            
            # 创建会话并设置Cookie
            session = self._create_session(cookie_id)
            self._update_session_cookies(session, cookie_value)
            
            # 检查登录状态
            if not await self._check_login_status(cookie_id, session):
                logger.error(f"账号 {cookie_id} 登录状态检查失败，无法添加到Token管理")
                return False
            
            # 获取初始Token
            token = await self._refresh_token(cookie_id, device_id, session)
            if not token:
                logger.error(f"账号 {cookie_id} 初始Token获取失败")
                return False
            
            # 创建TokenInfo
            token_info = TokenInfo(
                token=token,
                device_id=device_id,
                cookie_value=cookie_value,
                last_refresh_time=time.time(),
                expires_at=time.time() + self.token_expire_time,
                refresh_count=1,
                is_valid=True,
                error_count=0
            )
            
            self.tokens[cookie_id] = token_info
            
            # 启动定时刷新任务
            if self.is_running:
                await self._start_refresh_task(cookie_id)
            
            logger.info(f"账号 {cookie_id} 已添加到Token管理，Device ID: {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加账号 {cookie_id} 到Token管理失败: {e}")
            return False
    
    async def remove_account(self, cookie_id: str):
        """从Token管理中移除账号"""
        try:
            # 停止刷新任务
            if cookie_id in self.refresh_tasks:
                task = self.refresh_tasks.pop(cookie_id)
                if not task.done():
                    task.cancel()
            
            # 移除Token信息
            if cookie_id in self.tokens:
                del self.tokens[cookie_id]
            
            # 清理会话
            if cookie_id in self.session_pool:
                session = self.session_pool.pop(cookie_id)
                session.close()
            
            logger.info(f"账号 {cookie_id} 已从Token管理中移除")
            
        except Exception as e:
            logger.error(f"移除账号 {cookie_id} 失败: {e}")
    
    async def _start_refresh_task(self, cookie_id: str):
        """启动单个账号的Token刷新任务"""
        if cookie_id in self.refresh_tasks:
            logger.warning(f"账号 {cookie_id} 的Token刷新任务已存在")
            return
        
        async def refresh_loop():
            """Token刷新循环"""
            while self.is_running and cookie_id in self.tokens:
                try:
                    token_info = self.tokens[cookie_id]
                    
                    # 检查是否需要刷新
                    if token_info.needs_refresh(self.default_refresh_interval) or token_info.is_expired():
                        logger.info(f"开始刷新账号 {cookie_id} 的Token")
                        
                        session = self.session_pool.get(cookie_id)
                        if not session:
                            logger.error(f"账号 {cookie_id} 的会话不存在，跳过刷新")
                            await asyncio.sleep(self.retry_delay)
                            continue
                        
                        # 刷新Token
                        new_token = await self._refresh_token(cookie_id, token_info.device_id, session)
                        
                        if new_token:
                            # 更新Token信息
                            token_info.token = new_token
                            token_info.last_refresh_time = time.time()
                            token_info.expires_at = time.time() + self.token_expire_time
                            token_info.refresh_count += 1
                            token_info.error_count = 0
                            token_info.is_valid = True
                            
                            logger.info(f"账号 {cookie_id} Token刷新成功，刷新次数: {token_info.refresh_count}")
                        else:
                            # 刷新失败
                            token_info.error_count += 1
                            token_info.is_valid = False
                            
                            logger.error(f"账号 {cookie_id} Token刷新失败，错误次数: {token_info.error_count}")
                            
                            # 如果错误次数过多，标记为无效
                            if token_info.error_count >= self.max_error_count:
                                logger.error(f"账号 {cookie_id} Token刷新失败次数过多，标记为无效")
                                token_info.is_valid = False
                    
                    # 等待下次刷新
                    await asyncio.sleep(min(self.default_refresh_interval, 300))  # 最少5分钟检查一次
                    
                except asyncio.CancelledError:
                    logger.info(f"账号 {cookie_id} Token刷新任务被取消")
                    break
                except Exception as e:
                    logger.error(f"账号 {cookie_id} Token刷新任务异常: {e}")
                    await asyncio.sleep(self.retry_delay)
        
        # 创建并启动刷新任务
        task = asyncio.create_task(refresh_loop())
        self.refresh_tasks[cookie_id] = task
        logger.info(f"账号 {cookie_id} Token刷新任务已启动")
    
    async def start(self):
        """启动Token管理器"""
        if self.is_running:
            logger.warning("Token管理器已在运行")
            return
        
        self.is_running = True
        logger.info("Token管理器启动")
        
        # 为所有已添加的账号启动刷新任务
        for cookie_id in self.tokens.keys():
            await self._start_refresh_task(cookie_id)
        
        logger.info(f"已启动 {len(self.tokens)} 个账号的Token刷新任务")
    
    async def stop(self):
        """停止Token管理器"""
        logger.info("正在停止Token管理器...")
        self.is_running = False
        
        # 取消所有刷新任务
        for cookie_id, task in self.refresh_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.refresh_tasks.clear()
        
        # 关闭所有会话
        for session in self.session_pool.values():
            session.close()
        self.session_pool.clear()
        
        logger.info("Token管理器已停止")
    
    def get_token(self, cookie_id: str) -> Optional[str]:
        """获取指定账号的Token"""
        token_info = self.tokens.get(cookie_id)
        if token_info and token_info.is_valid:
            return token_info.token
        return None
    
    def is_token_valid(self, cookie_id: str) -> bool:
        """检查指定账号的Token是否有效"""
        token_info = self.tokens.get(cookie_id)
        return token_info is not None and token_info.is_valid and not token_info.is_expired()
    
    def get_token_info(self, cookie_id: str) -> Optional[TokenInfo]:
        """获取指定账号的Token信息"""
        return self.tokens.get(cookie_id)
    
    def get_all_tokens_status(self) -> Dict[str, dict]:
        """获取所有账号的Token状态"""
        status = {}
        for cookie_id, token_info in self.tokens.items():
            status[cookie_id] = {
                'is_valid': token_info.is_valid,
                'is_expired': token_info.is_expired(),
                'needs_refresh': token_info.needs_refresh(self.default_refresh_interval),
                'last_refresh_time': token_info.last_refresh_time,
                'refresh_count': token_info.refresh_count,
                'error_count': token_info.error_count,
                'expires_at': token_info.expires_at
            }
        return status
    
    async def force_refresh_token(self, cookie_id: str) -> bool:
        """强制刷新指定账号的Token"""
        try:
            token_info = self.tokens.get(cookie_id)
            if not token_info:
                logger.error(f"账号 {cookie_id} 不存在，无法强制刷新Token")
                return False
            
            session = self.session_pool.get(cookie_id)
            if not session:
                logger.error(f"账号 {cookie_id} 的会话不存在，无法强制刷新Token")
                return False
            
            logger.info(f"开始强制刷新账号 {cookie_id} 的Token")
            
            new_token = await self._refresh_token(cookie_id, token_info.device_id, session)
            
            if new_token:
                token_info.token = new_token
                token_info.last_refresh_time = time.time()
                token_info.expires_at = time.time() + self.token_expire_time
                token_info.refresh_count += 1
                token_info.error_count = 0
                token_info.is_valid = True
                
                logger.info(f"账号 {cookie_id} Token强制刷新成功")
                return True
            else:
                logger.error(f"账号 {cookie_id} Token强制刷新失败")
                return False
                
        except Exception as e:
            logger.error(f"强制刷新账号 {cookie_id} Token异常: {e}")
            return False
    
    async def batch_refresh_tokens(self, cookie_ids: List[str] = None) -> Dict[str, bool]:
        """批量刷新Token"""
        if cookie_ids is None:
            cookie_ids = list(self.tokens.keys())
        
        logger.info(f"开始批量刷新 {len(cookie_ids)} 个账号的Token")
        
        results = {}
        for cookie_id in cookie_ids:
            results[cookie_id] = await self.force_refresh_token(cookie_id)
        
        success_count = sum(results.values())
        logger.info(f"批量刷新完成，成功: {success_count}/{len(cookie_ids)}")
        
        return results


# 全局Token管理器实例
token_manager = XianyuTokenManager()