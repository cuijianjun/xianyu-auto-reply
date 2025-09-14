import logging
import sys
from typing import Optional
from contextvars import ContextVar

# 创建上下文变量用于追踪
trace_context: ContextVar[Optional[str]] = ContextVar('trace_context', default=None)

class TraceContext:
    """追踪上下文管理器"""
    
    def __init__(self, trace_id: str):
        self.trace_id = trace_id
        self.token = None
    
    def __enter__(self):
        self.token = trace_context.set(self.trace_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            trace_context.reset(self.token)
    
    @staticmethod
    def generate_trace_id() -> str:
        """生成追踪ID"""
        import uuid
        return str(uuid.uuid4())[:8]

class LoggerManager:
    """日志管理器"""
    
    def __init__(self, name: str = __name__, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 如果没有处理器，添加控制台处理器
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def get_logger(self):
        """获取logger实例"""
        return self.logger
    
    def info(self, message: str):
        """记录信息日志"""
        trace_id = trace_context.get()
        if trace_id:
            message = f"[{trace_id}] {message}"
        self.logger.info(message)
    
    def error(self, message: str):
        """记录错误日志"""
        trace_id = trace_context.get()
        if trace_id:
            message = f"[{trace_id}] {message}"
        self.logger.error(message)
    
    def warning(self, message: str):
        """记录警告日志"""
        trace_id = trace_context.get()
        if trace_id:
            message = f"[{trace_id}] {message}"
        self.logger.warning(message)
    
    def debug(self, message: str):
        """记录调试日志"""
        trace_id = trace_context.get()
        if trace_id:
            message = f"[{trace_id}] {message}"
        self.logger.debug(message)

# 创建默认的日志管理器实例
default_logger = LoggerManager()