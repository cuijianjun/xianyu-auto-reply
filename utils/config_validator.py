"""
配置验证工具模块

用于验证配置文件的有效性和完整性，确保所有必要的配置项都存在且格式正确。
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from loguru import logger


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self, config_path: str = None):
        """初始化配置验证器
        
        Args:
            config_path: 配置文件路径，默认为global_config.yml
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'global_config.yml')
        self.config_path = config_path
        self.config = {}
        self.errors = []
        self.warnings = []
    
    def load_config(self) -> bool:
        """加载配置文件
        
        Returns:
            bool: 加载是否成功
        """
        try:
            if not os.path.exists(self.config_path):
                self.errors.append(f"配置文件不存在: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            if not isinstance(self.config, dict):
                self.errors.append("配置文件格式错误，根节点必须是字典")
                return False
            
            return True
        except yaml.YAMLError as e:
            self.errors.append(f"配置文件YAML格式错误: {e}")
            return False
        except Exception as e:
            self.errors.append(f"加载配置文件失败: {e}")
            return False
    
    def validate_required_sections(self) -> bool:
        """验证必需的配置节
        
        Returns:
            bool: 验证是否通过
        """
        required_sections = [
            'API_ENDPOINTS',
            'APP_CONFIG',
            'AUTO_REPLY',
            'COOKIES',
            'DEFAULT_HEADERS',
            'WEBSOCKET_HEADERS',
            'WEBSOCKET_URL'
        ]
        
        success = True
        for section in required_sections:
            if section not in self.config:
                self.errors.append(f"缺少必需的配置节: {section}")
                success = False
        
        return success
    
    def validate_websocket_enhanced(self) -> bool:
        """验证WebSocket增强配置
        
        Returns:
            bool: 验证是否通过
        """
        if 'WEBSOCKET_ENHANCED' not in self.config:
            self.warnings.append("未找到WEBSOCKET_ENHANCED配置，将使用默认值")
            return True
        
        ws_config = self.config['WEBSOCKET_ENHANCED']
        success = True
        
        # 验证连接配置
        if 'connection' in ws_config:
            conn_config = ws_config['connection']
            if not isinstance(conn_config.get('timeout'), (int, float)) or conn_config.get('timeout') <= 0:
                self.errors.append("WEBSOCKET_ENHANCED.connection.timeout 必须是正数")
                success = False
            
            if not isinstance(conn_config.get('max_reconnect_attempts'), int) or conn_config.get('max_reconnect_attempts') < 0:
                self.errors.append("WEBSOCKET_ENHANCED.connection.max_reconnect_attempts 必须是非负整数")
                success = False
        
        # 验证心跳配置
        if 'heartbeat' in ws_config:
            hb_config = ws_config['heartbeat']
            if not isinstance(hb_config.get('interval'), (int, float)) or hb_config.get('interval') <= 0:
                self.errors.append("WEBSOCKET_ENHANCED.heartbeat.interval 必须是正数")
                success = False
        
        return success
    
    def validate_token_manager(self) -> bool:
        """验证Token管理器配置
        
        Returns:
            bool: 验证是否通过
        """
        if 'TOKEN_MANAGER' not in self.config:
            self.warnings.append("未找到TOKEN_MANAGER配置，将使用默认值")
            return True
        
        token_config = self.config['TOKEN_MANAGER']
        success = True
        
        # 验证刷新配置
        if 'refresh' in token_config:
            refresh_config = token_config['refresh']
            if not isinstance(refresh_config.get('interval'), (int, float)) or refresh_config.get('interval') <= 0:
                self.errors.append("TOKEN_MANAGER.refresh.interval 必须是正数")
                success = False
            
            if not isinstance(refresh_config.get('batch_size'), int) or refresh_config.get('batch_size') <= 0:
                self.errors.append("TOKEN_MANAGER.refresh.batch_size 必须是正整数")
                success = False
        
        # 验证会话配置
        if 'session' in token_config:
            session_config = token_config['session']
            if not isinstance(session_config.get('pool_size'), int) or session_config.get('pool_size') <= 0:
                self.errors.append("TOKEN_MANAGER.session.pool_size 必须是正整数")
                success = False
        
        return success
    
    def validate_cookie_manager_enhanced(self) -> bool:
        """验证Cookie管理器增强配置
        
        Returns:
            bool: 验证是否通过
        """
        if 'COOKIE_MANAGER_ENHANCED' not in self.config:
            self.warnings.append("未找到COOKIE_MANAGER_ENHANCED配置，将使用默认值")
            return True
        
        cookie_config = self.config['COOKIE_MANAGER_ENHANCED']
        success = True
        
        # 验证同步配置
        if 'sync' in cookie_config:
            sync_config = cookie_config['sync']
            valid_resolutions = ['latest', 'manual', 'merge']
            if sync_config.get('conflict_resolution') not in valid_resolutions:
                self.errors.append(f"COOKIE_MANAGER_ENHANCED.sync.conflict_resolution 必须是以下值之一: {valid_resolutions}")
                success = False
        
        # 验证备份配置
        if 'backup' in cookie_config:
            backup_config = cookie_config['backup']
            if backup_config.get('enabled') and not isinstance(backup_config.get('max_backups'), int):
                self.errors.append("COOKIE_MANAGER_ENHANCED.backup.max_backups 必须是整数")
                success = False
        
        return success
    
    def validate_connection_monitor(self) -> bool:
        """验证连接监控配置
        
        Returns:
            bool: 验证是否通过
        """
        if 'CONNECTION_MONITOR' not in self.config:
            self.warnings.append("未找到CONNECTION_MONITOR配置，将使用默认值")
            return True
        
        monitor_config = self.config['CONNECTION_MONITOR']
        success = True
        
        # 验证健康检查端点
        if 'health_check' in monitor_config and 'endpoints' in monitor_config['health_check']:
            endpoints = monitor_config['health_check']['endpoints']
            if not isinstance(endpoints, list):
                self.errors.append("CONNECTION_MONITOR.health_check.endpoints 必须是列表")
                success = False
            else:
                for i, endpoint in enumerate(endpoints):
                    if not isinstance(endpoint, dict):
                        self.errors.append(f"CONNECTION_MONITOR.health_check.endpoints[{i}] 必须是字典")
                        success = False
                        continue
                    
                    if 'url' not in endpoint:
                        self.errors.append(f"CONNECTION_MONITOR.health_check.endpoints[{i}] 缺少url字段")
                        success = False
        
        return success
    
    def validate_performance(self) -> bool:
        """验证性能配置
        
        Returns:
            bool: 验证是否通过
        """
        if 'PERFORMANCE' not in self.config:
            self.warnings.append("未找到PERFORMANCE配置，将使用默认值")
            return True
        
        perf_config = self.config['PERFORMANCE']
        success = True
        
        # 验证异步优化配置
        if 'async_optimization' in perf_config:
            async_config = perf_config['async_optimization']
            if not isinstance(async_config.get('max_concurrent_connections'), int) or async_config.get('max_concurrent_connections') <= 0:
                self.errors.append("PERFORMANCE.async_optimization.max_concurrent_connections 必须是正整数")
                success = False
        
        # 验证内存管理配置
        if 'memory_management' in perf_config:
            mem_config = perf_config['memory_management']
            cleanup_threshold = mem_config.get('cleanup_threshold')
            if cleanup_threshold is not None and (not isinstance(cleanup_threshold, (int, float)) or not 0 < cleanup_threshold <= 1):
                self.errors.append("PERFORMANCE.memory_management.cleanup_threshold 必须是0到1之间的数值")
                success = False
        
        return success
    
    def validate_all(self) -> bool:
        """执行完整的配置验证
        
        Returns:
            bool: 验证是否通过
        """
        if not self.load_config():
            return False
        
        success = True
        success &= self.validate_required_sections()
        success &= self.validate_websocket_enhanced()
        success &= self.validate_token_manager()
        success &= self.validate_cookie_manager_enhanced()
        success &= self.validate_connection_monitor()
        success &= self.validate_performance()
        
        return success
    
    def get_validation_report(self) -> Dict[str, Any]:
        """获取验证报告
        
        Returns:
            Dict[str, Any]: 包含错误和警告信息的报告
        """
        return {
            'success': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }
    
    def print_report(self) -> None:
        """打印验证报告"""
        report = self.get_validation_report()
        
        if report['success']:
            logger.info("✅ 配置验证通过")
        else:
            logger.error("❌ 配置验证失败")
        
        if report['errors']:
            logger.error(f"发现 {report['error_count']} 个错误:")
            for error in report['errors']:
                logger.error(f"  - {error}")
        
        if report['warnings']:
            logger.warning(f"发现 {report['warning_count']} 个警告:")
            for warning in report['warnings']:
                logger.warning(f"  - {warning}")


def validate_config(config_path: str = None, print_report: bool = True) -> bool:
    """验证配置文件的便捷函数
    
    Args:
        config_path: 配置文件路径
        print_report: 是否打印验证报告
    
    Returns:
        bool: 验证是否通过
    """
    validator = ConfigValidator(config_path)
    success = validator.validate_all()
    
    if print_report:
        validator.print_report()
    
    return success


if __name__ == "__main__":
    # 直接运行时执行配置验证
    validate_config()