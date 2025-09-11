import asyncio
import websockets
from typing import Optional, Dict, Any, Callable
from loguru import logger

class WebSocketClient:
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