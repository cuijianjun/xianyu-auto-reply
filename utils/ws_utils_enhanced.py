import asyncio
import websockets
import json
import time
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from loguru import logger
from dataclasses import dataclass


class ConnectionState(Enum):
    """WebSocket连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ConnectionStats:
    """连接统计信息"""
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    total_reconnects: int = 0
    last_connect_time: Optional[float] = None
    last_disconnect_time: Optional[float] = None
    uptime_seconds: float = 0.0
    
    def get_success_rate(self) -> float:
        """获取连接成功率"""
        if self.total_connections == 0:
            return 0.0
        return self.successful_connections / self.total_connections * 100


class HeartbeatManager:
    """心跳管理器"""
    
    def __init__(self, interval: int = 30, timeout: int = 10):
        self.interval = interval  # 心跳间隔（秒）
        self.timeout = timeout    # 心跳超时（秒）
        self.last_pong = time.time()
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.is_running = False
        
    async def start(self, websocket_client):
        """启动心跳"""
        if self.is_running:
            return
            
        self.is_running = True
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop(websocket_client))
        logger.info(f"心跳管理器启动，间隔: {self.interval}秒")
        
    async def stop(self):
        """停止心跳"""
        self.is_running = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("心跳管理器已停止")
        
    async def _heartbeat_loop(self, websocket_client):
        """心跳循环"""
        while self.is_running:
            try:
                await asyncio.sleep(self.interval)
                
                if not websocket_client.is_connected:
                    continue
                    
                # 发送ping
                ping_data = json.dumps({
                    "type": "ping",
                    "timestamp": time.time()
                })
                
                success = await websocket_client.send(ping_data)
                if not success:
                    logger.warning("心跳发送失败，连接可能已断开")
                    continue
                    
                # 检查是否超时
                if time.time() - self.last_pong > self.timeout:
                    logger.warning("心跳超时，触发重连")
                    await websocket_client._set_connection_state(ConnectionState.DISCONNECTED)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳循环异常: {e}")
                
    def on_pong_received(self):
        """收到pong响应"""
        self.last_pong = time.time()


class WebSocketClient:
    def __init__(self, url: str, headers: Dict[str, str], on_message: Callable[[Dict[str, Any]], None],
                 heartbeat_interval: int = 30, heartbeat_timeout: int = 10):
        """初始化WebSocket客户端"""
        self.url = url
        self.headers = headers
        self.on_message = on_message
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.connection_state = ConnectionState.DISCONNECTED
        
        # 重连配置
        self.base_reconnect_delay = 3  # 基础重连延迟，单位秒
        self.max_reconnect_delay = 300  # 最大重连延迟，5分钟
        self.reconnect_backoff_factor = 2  # 指数退避因子
        self.current_reconnect_delay = self.base_reconnect_delay
        self.max_retry_attempts = 50  # 最大重试次数
        self.retry_count = 0  # 当前重试次数
        
        # 连接监控
        self.stats = ConnectionStats()
        self.heartbeat_manager = HeartbeatManager(heartbeat_interval, heartbeat_timeout)
        self.connection_listeners: List[Callable[[ConnectionState], None]] = []
        
        # 任务管理
        self.message_handler_task: Optional[asyncio.Task] = None
        self.is_running = False
        
    def add_connection_listener(self, listener: Callable[[ConnectionState], None]):
        """添加连接状态监听器"""
        self.connection_listeners.append(listener)
        
    def remove_connection_listener(self, listener: Callable[[ConnectionState], None]):
        """移除连接状态监听器"""
        if listener in self.connection_listeners:
            self.connection_listeners.remove(listener)
            
    async def _set_connection_state(self, state: ConnectionState):
        """设置连接状态并通知监听器"""
        if self.connection_state != state:
            old_state = self.connection_state
            self.connection_state = state
            self.is_connected = (state == ConnectionState.CONNECTED)
            
            logger.info(f"连接状态变更: {old_state.value} -> {state.value}")
            
            # 通知监听器
            for listener in self.connection_listeners:
                try:
                    await listener(state) if asyncio.iscoroutinefunction(listener) else listener(state)
                except Exception as e:
                    logger.error(f"连接状态监听器异常: {e}")
                    
    def get_connection_stats(self) -> ConnectionStats:
        """获取连接统计信息"""
        if self.is_connected and self.stats.last_connect_time:
            self.stats.uptime_seconds = time.time() - self.stats.last_connect_time
        return self.stats
        
    async def connect(self):
        """建立WebSocket连接"""
        await self._set_connection_state(ConnectionState.CONNECTING)
        self.stats.total_connections += 1
        
        try:
            self.websocket = await websockets.connect(
                self.url,
                extra_headers=self.headers,
                ping_interval=None,
                ping_timeout=None
            )
            
            self.stats.successful_connections += 1
            self.stats.last_connect_time = time.time()
            await self._set_connection_state(ConnectionState.CONNECTED)
            
            # 启动心跳
            await self.heartbeat_manager.start(self)
            
            logger.info("WebSocket连接建立成功")
            return True
            
        except Exception as e:
            self.stats.failed_connections += 1
            await self._set_connection_state(ConnectionState.FAILED)
            logger.error(f"WebSocket连接失败: {e}")
            return False
            
    async def disconnect(self):
        """关闭WebSocket连接"""
        await self._set_connection_state(ConnectionState.DISCONNECTED)
        
        # 停止心跳
        await self.heartbeat_manager.stop()
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"关闭WebSocket连接时出现异常: {e}")
                
        self.stats.last_disconnect_time = time.time()
        logger.info("WebSocket连接已关闭")
            
    async def send(self, message: str):
        """发送消息"""
        if not self.is_connected or not self.websocket:
            logger.warning("WebSocket未连接，无法发送消息")
            return False
            
        try:
            await self.websocket.send(message)
            return True
        except Exception as e:
            logger.error(f"消息发送失败: {e}")
            await self._set_connection_state(ConnectionState.DISCONNECTED)
            return False
            
    async def receive(self):
        """接收消息"""
        if not self.is_connected or not self.websocket:
            logger.warning("WebSocket未连接，无法接收消息")
            return None
            
        try:
            message = await self.websocket.recv()
            
            # 处理心跳响应
            try:
                data = json.loads(message)
                if data.get("type") == "pong":
                    self.heartbeat_manager.on_pong_received()
                    return None  # 心跳响应不传递给业务层
            except (json.JSONDecodeError, KeyError):
                pass  # 不是JSON或不是心跳消息，继续处理
                
            return message
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket连接已关闭")
            await self._set_connection_state(ConnectionState.DISCONNECTED)
            return None
        except Exception as e:
            logger.error(f"消息接收失败: {e}")
            await self._set_connection_state(ConnectionState.DISCONNECTED)
            return None
            
    async def reconnect(self):
        """重新连接"""
        await self._set_connection_state(ConnectionState.RECONNECTING)
        self.retry_count += 1
        self.stats.total_reconnects += 1
        
        # 检查是否超过最大重试次数
        if self.retry_count > self.max_retry_attempts:
            logger.error(f"已达到最大重试次数 {self.max_retry_attempts}，停止重连")
            await self._set_connection_state(ConnectionState.FAILED)
            return False
            
        logger.info(f"准备在{self.current_reconnect_delay}秒后重新连接... (第{self.retry_count}次重试)")
        await asyncio.sleep(self.current_reconnect_delay)
        
        # 指数退避：增加下次重连延迟
        self.current_reconnect_delay = min(
            self.current_reconnect_delay * self.reconnect_backoff_factor,
            self.max_reconnect_delay
        )
        
        success = await self.connect()
        if success:
            # 连接成功，重置重试计数和延迟
            self.retry_count = 0
            self.current_reconnect_delay = self.base_reconnect_delay
            logger.info("WebSocket重连成功，重置重试计数")
            
        return success
        
    async def start(self):
        """启动WebSocket客户端"""
        if self.is_running:
            logger.warning("WebSocket客户端已在运行")
            return
            
        self.is_running = True
        logger.info("启动WebSocket客户端")
        
        while self.is_running:
            if not self.is_connected:
                success = await self.connect()
                if not success:
                    if not await self.reconnect():
                        break
                    continue
                    
            try:
                message = await self.receive()
                if message and self.on_message:
                    if asyncio.iscoroutinefunction(self.on_message):
                        await self.on_message(message)
                    else:
                        self.on_message(message)
            except Exception as e:
                logger.error(f"消息处理失败: {e}")
                await self.disconnect()
                if self.is_running:
                    await self.reconnect()
                    
    async def stop(self):
        """停止WebSocket客户端"""
        logger.info("停止WebSocket客户端")
        self.is_running = False
        await self.disconnect()
        
    async def run(self):
        """运行WebSocket客户端（兼容原有接口）"""
        await self.start()


# 工具函数
def create_enhanced_websocket_client(url: str, headers: Dict[str, str], 
                                   on_message: Callable[[Dict[str, Any]], None],
                                   heartbeat_interval: int = 30,
                                   heartbeat_timeout: int = 10) -> WebSocketClient:
    """创建增强的WebSocket客户端"""
    return WebSocketClient(url, headers, on_message, heartbeat_interval, heartbeat_timeout)


async def test_websocket_connection(url: str, headers: Dict[str, str], timeout: int = 10) -> bool:
    """测试WebSocket连接"""
    try:
        async with asyncio.wait_for(
            websockets.connect(url, extra_headers=headers), 
            timeout=timeout
        ) as websocket:
            await websocket.ping()
            return True
    except Exception as e:
        logger.error(f"WebSocket连接测试失败: {e}")
        return False