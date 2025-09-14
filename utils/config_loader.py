"""
配置加载器 - 为Cookie自动更新功能提供配置支持

提供便捷的配置读取接口，支持环境变量覆盖和默认值设置
"""

import os
from typing import Any, Dict
from config import Config
from loguru import logger


class CookieAutoUpdateConfig:
    """Cookie自动更新配置管理器"""
    
    def __init__(self):
        self.config = Config()
        self._load_config()
    
    def _load_config(self):
        """加载Cookie自动更新相关配置"""
        try:
            # 从配置文件获取Cookie自动更新配置
            cookie_config = self.config.get('COOKIE_AUTO_UPDATE', {})
            
            # 配置项映射
            self.enabled = self._get_bool_config('enabled', cookie_config, True)
            self.refresh_interval = self._get_int_config('refresh_interval', cookie_config, 3600)
            self.retry_interval = self._get_int_config('retry_interval', cookie_config, 300)
            self.batch_size = self._get_int_config('batch_size', cookie_config, 5)
            self.timeout = self._get_int_config('timeout', cookie_config, 30)
            self.auto_start = self._get_bool_config('auto_start', cookie_config, True)
            self.log_level = cookie_config.get('log_level', 'INFO')
            
            logger.info(f"Cookie自动更新配置加载完成: enabled={self.enabled}, refresh_interval={self.refresh_interval}s")
            
        except Exception as e:
            logger.error(f"加载Cookie自动更新配置失败: {e}")
            # 使用默认配置
            self._set_default_config()
    
    def _get_bool_config(self, key: str, config_dict: Dict, default: bool) -> bool:
        """获取布尔类型配置，支持环境变量覆盖"""
        env_key = f"COOKIE_AUTO_UPDATE_{key.upper()}"
        env_value = os.getenv(env_key)
        
        if env_value is not None:
            return env_value.lower() in ('true', '1', 'yes', 'on')
        
        return config_dict.get(key, default)
    
    def _get_int_config(self, key: str, config_dict: Dict, default: int) -> int:
        """获取整数类型配置，支持环境变量覆盖"""
        env_key = f"COOKIE_AUTO_UPDATE_{key.upper()}"
        env_value = os.getenv(env_key)
        
        if env_value is not None:
            try:
                return int(env_value)
            except ValueError:
                logger.warning(f"环境变量 {env_key} 值无效: {env_value}，使用默认值: {default}")
        
        return config_dict.get(key, default)
    
    def _set_default_config(self):
        """设置默认配置"""
        self.enabled = True
        self.refresh_interval = 3600
        self.retry_interval = 300
        self.batch_size = 5
        self.timeout = 30
        self.auto_start = True
        self.log_level = 'INFO'
        
        logger.info("使用默认Cookie自动更新配置")
    
    def get_config_dict(self) -> Dict[str, Any]:
        """获取配置字典"""
        return {
            'enabled': self.enabled,
            'refresh_interval': self.refresh_interval,
            'retry_interval': self.retry_interval,
            'batch_size': self.batch_size,
            'timeout': self.timeout,
            'auto_start': self.auto_start,
            'log_level': self.log_level
        }
    
    def update_config(self, **kwargs):
        """动态更新配置"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"更新Cookie自动更新配置: {key} = {value}")
            else:
                logger.warning(f"未知的配置项: {key}")
    
    def is_enabled(self) -> bool:
        """检查是否启用Cookie自动更新"""
        return self.enabled
    
    def should_auto_start(self) -> bool:
        """检查是否应该自动启动"""
        return self.auto_start


# 全局配置实例
cookie_auto_update_config = CookieAutoUpdateConfig()