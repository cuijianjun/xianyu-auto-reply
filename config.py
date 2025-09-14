import os
import yaml
import threading
from typing import Dict, Any

class Config:
    """配置管理类
    
    用于加载和管理全局配置文件(global_config.yml)。
    支持配置的读取、修改和保存。
    """
    
    _instance = None
    _config = {}
    _lock = threading.Lock()  # 线程锁保护单例创建

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:  # 使用双重检查锁定模式
                if cls._instance is None:
                    cls._instance = super(Config, cls).__new__(cls)
                    cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置文件
        
        从global_config.yml文件中加载配置信息。
        如果文件不存在则抛出FileNotFoundError异常。
        """
        config_path = os.path.join(os.path.dirname(__file__), 'global_config.yml')
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项
        
        Args:
            key: 配置项的键，支持点号分隔的多级键
            default: 当配置项不存在时返回的默认值
            
        Returns:
            配置项的值或默认值
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """设置配置项
        
        Args:
            key: 配置项的键，支持点号分隔的多级键
            value: 要设置的值
        """
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def save(self) -> None:
        """保存配置到文件
        
        将当前配置保存回global_config.yml文件
        """
        config_path = os.path.join(os.path.dirname(__file__), 'global_config.yml')
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self._config, f, allow_unicode=True, default_flow_style=False)

    @property
    def config(self) -> Dict[str, Any]:
        """获取完整配置
        
        Returns:
            包含所有配置项的字典
        """
        return self._config

# 创建全局配置实例
config = Config()

# 导出常用配置项
COOKIES_STR = config.get('COOKIES.value', '')
COOKIES_LAST_UPDATE = config.get('COOKIES.last_update_time', '')
WEBSOCKET_URL = config.get('WEBSOCKET_URL', 'wss://wss-goofish.dingtalk.com/')
HEARTBEAT_INTERVAL = config.get('HEARTBEAT_INTERVAL', 15)
HEARTBEAT_TIMEOUT = config.get('HEARTBEAT_TIMEOUT', 5)
TOKEN_REFRESH_INTERVAL = config.get('TOKEN_REFRESH_INTERVAL', 3600)
TOKEN_RETRY_INTERVAL = config.get('TOKEN_RETRY_INTERVAL', 300)
MESSAGE_EXPIRE_TIME = config.get('MESSAGE_EXPIRE_TIME', 300000)
API_ENDPOINTS = config.get('API_ENDPOINTS', {})
DEFAULT_HEADERS = config.get('DEFAULT_HEADERS', {})
WEBSOCKET_HEADERS = config.get('WEBSOCKET_HEADERS', {})
APP_CONFIG = config.get('APP_CONFIG', {})
AUTO_REPLY = config.get('AUTO_REPLY', {
    'enabled': True,
    'default_message': '亲爱的"{send_user_name}" 老板你好！所有宝贝都可以拍，秒发货的哈~不满意的话可以直接申请退款哈~',
    'api': {
        'enabled': False,
        'url': 'http://localhost:8080/xianyu/reply',
        'timeout': 10
    }
})
MANUAL_MODE = config.get('MANUAL_MODE', {})
LOG_CONFIG = config.get('LOG_CONFIG', {}) 
_cookies_raw = config.get('COOKIES', [])
if isinstance(_cookies_raw, list):
    COOKIES_LIST = _cookies_raw
else:
    # 兼容旧格式，仅有 value 字段
    val = _cookies_raw.get('value') if isinstance(_cookies_raw, dict) else None
    COOKIES_LIST = [{'id': 'default', 'value': val}] if val else []

# 长连接增强配置
WEBSOCKET_ENHANCED = config.get('WEBSOCKET_ENHANCED', {
    'enabled': True,
    'connection': {
        'timeout': 30,
        'max_reconnect_attempts': 10,
        'reconnect_delay': 3,
        'max_reconnect_delay': 300,
        'exponential_backoff_factor': 2,
        'connection_check_interval': 60
    },
    'heartbeat': {
        'enabled': True,
        'interval': 15,
        'timeout': 30,
        'max_missed_heartbeats': 3,
        'adaptive_interval': True
    },
    'statistics': {
        'enabled': True,
        'log_interval': 300,
        'reset_interval': 86400
    }
})

# Token管理增强配置
TOKEN_MANAGER_CONFIG = config.get('TOKEN_MANAGER', {
    'enabled': True,
    'refresh': {
        'interval': 3600,
        'retry_interval': 300,
        'max_retry_attempts': 5,
        'batch_size': 3,
        'timeout': 30,
        'preemptive_refresh': True,
        'preemptive_threshold': 300
    },
    'validation': {
        'enabled': True,
        'interval': 1800,
        'timeout': 15,
        'retry_on_failure': True
    },
    'session': {
        'pool_size': 10,
        'keep_alive': True,
        'timeout': 30,
        'max_retries': 3
    },
    'logging': {
        'level': 'INFO',
        'detailed': False
    }
})

# Cookie管理增强配置
COOKIE_MANAGER_ENHANCED = config.get('COOKIE_MANAGER_ENHANCED', {
    'enabled': True,
    'sync': {
        'auto_sync': True,
        'sync_interval': 60,
        'conflict_resolution': 'latest'
    },
    'validation': {
        'enabled': True,
        'check_interval': 1800,
        'auto_refresh_on_invalid': True
    },
    'backup': {
        'enabled': True,
        'backup_interval': 3600,
        'max_backups': 24,
        'backup_path': './data/cookie_backups'
    },
    'cleanup': {
        'enabled': True,
        'cleanup_interval': 86400,
        'retention_days': 7
    }
})

# 连接监控配置
CONNECTION_MONITOR = config.get('CONNECTION_MONITOR', {
    'enabled': True,
    'metrics': {
        'collect_detailed': True,
        'retention_hours': 24,
        'export_interval': 300
    },
    'alerts': {
        'enabled': True,
        'connection_failure_threshold': 5,
        'token_refresh_failure_threshold': 3,
        'response_time_threshold': 5000
    },
    'health_check': {
        'enabled': True,
        'interval': 60,
        'timeout': 10,
        'endpoints': [
            {
                'url': 'https://passport.goofish.com/newlogin/hasLogin.do',
                'method': 'GET',
                'expected_status': 200,
                'timeout': 5
            }
        ]
    }
})

# 性能优化配置
PERFORMANCE_CONFIG = config.get('PERFORMANCE', {
    'async_optimization': {
        'enabled': True,
        'max_concurrent_connections': 5,
        'connection_pool_size': 10,
        'request_timeout': 30
    },
    'memory_management': {
        'enabled': True,
        'gc_interval': 300,
        'max_memory_usage': 512,
        'cleanup_threshold': 0.8
    },
    'caching': {
        'enabled': True,
        'token_cache_ttl': 3600,
        'response_cache_ttl': 300,
        'max_cache_size': 1000
    }
})

# 便捷访问的配置项
WS_ENHANCED_ENABLED = WEBSOCKET_ENHANCED.get('enabled', True)
WS_CONNECTION_TIMEOUT = WEBSOCKET_ENHANCED.get('connection', {}).get('timeout', 30)
WS_MAX_RECONNECT_ATTEMPTS = WEBSOCKET_ENHANCED.get('connection', {}).get('max_reconnect_attempts', 10)
WS_RECONNECT_DELAY = WEBSOCKET_ENHANCED.get('connection', {}).get('reconnect_delay', 3)
WS_HEARTBEAT_INTERVAL = WEBSOCKET_ENHANCED.get('heartbeat', {}).get('interval', 15)
WS_HEARTBEAT_TIMEOUT = WEBSOCKET_ENHANCED.get('heartbeat', {}).get('timeout', 30)

TOKEN_MANAGER_ENABLED = TOKEN_MANAGER_CONFIG.get('enabled', True)
TOKEN_REFRESH_INTERVAL_ENHANCED = TOKEN_MANAGER_CONFIG.get('refresh', {}).get('interval', 3600)
TOKEN_RETRY_INTERVAL_ENHANCED = TOKEN_MANAGER_CONFIG.get('refresh', {}).get('retry_interval', 300)
TOKEN_MAX_RETRY_ATTEMPTS = TOKEN_MANAGER_CONFIG.get('refresh', {}).get('max_retry_attempts', 5)
TOKEN_BATCH_SIZE = TOKEN_MANAGER_CONFIG.get('refresh', {}).get('batch_size', 3)

COOKIE_MANAGER_ENHANCED_ENABLED = COOKIE_MANAGER_ENHANCED.get('enabled', True)
COOKIE_SYNC_INTERVAL = COOKIE_MANAGER_ENHANCED.get('sync', {}).get('sync_interval', 60)
COOKIE_BACKUP_ENABLED = COOKIE_MANAGER_ENHANCED.get('backup', {}).get('enabled', True)
COOKIE_BACKUP_INTERVAL = COOKIE_MANAGER_ENHANCED.get('backup', {}).get('backup_interval', 3600)

CONNECTION_MONITOR_ENABLED = CONNECTION_MONITOR.get('enabled', True)
HEALTH_CHECK_INTERVAL = CONNECTION_MONITOR.get('health_check', {}).get('interval', 60)
PERFORMANCE_OPTIMIZATION_ENABLED = PERFORMANCE_CONFIG.get('async_optimization', {}).get('enabled', True)
MAX_CONCURRENT_CONNECTIONS = PERFORMANCE_CONFIG.get('async_optimization', {}).get('max_concurrent_connections', 5) 