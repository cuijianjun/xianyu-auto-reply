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
                    websocket_client.is_connected = False
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳循环异常: {e}")
                
    def on_pong_received(self):
        """收到pong响应"""
        self.last_pong = time.time()


class WebSocketClient:
=======
    def __init__(self, url: str, headers: Dict[str, str], on_message: Callable[[Dict[str, Any]], None]):
        """初始化WebSocket客户端"""
        self.url = url
        self.headers = headers
        self.on_message = on_message
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        
        # 重连配置
        self.base_reconnect_delay = 3  # 基础重连延迟，单位秒
        self.max_reconnect_delay = 300  # 最大重连延迟，5分钟
        self.reconnect_backoff_factor = 2  # 指数退避因子
        self.current_reconnect_delay = self.base_reconnect_delay
        self.max_retry_attempts = 50  # 最大重试次数
        self.retry_count = 0  # 当前重试次数
        
    async def connect(self):
        """建立WebSocket连接"""
        try:
            self.websocket = await websockets.connect(
                self.url,
                extra_headers=self.headers,
                ping_interval=None,
                ping_timeout=None
            )
            self.is_connected = True
            logger.info("WebSocket连接建立成功")
            return True
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
            return False
            
    async def disconnect(self):
        """关闭WebSocket连接"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("WebSocket连接已关闭")
            
    async def send(self, message: str):
        """发送消息"""
        if not self.is_connected:
            logger.warning("WebSocket未连接，无法发送消息")
            return False
            
        try:
            await self.websocket.send(message)
            return True
        except Exception as e:
            logger.error(f"消息发送失败: {e}")
            self.is_connected = False
            return False
            
    async def receive(self):
        """接收消息"""
        if not self.is_connected:
            logger.warning("WebSocket未连接，无法接收消息")
            return None
            
        try:
            message = await self.websocket.recv()
            return message
        except Exception as e:
            logger.error(f"消息接收失败: {e}")
            self.is_connected = False
            return None
            
    async def reconnect(self):
        """重新连接"""
        self.retry_count += 1
        
        # 检查是否超过最大重试次数
        if self.retry_count > self.max_retry_attempts:
            logger.error(f"已达到最大重试次数 {self.max_retry_attempts}，停止重连")
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
        
    async def run(self):
        """运行WebSocket客户端"""
        while True:
            if not self.is_connected:
                success = await self.connect()
                if not success:
                    await self.reconnect()
                    continue
                    
            try:
                message = await self.receive()
                if message:
                    await self.on_message(message)
            except Exception as e:
                logger.error(f"消息处理失败: {e}")
                await self.disconnect()
                await self.reconnect() 