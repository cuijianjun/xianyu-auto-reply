# Cookie 自动刷新功能使用指南

## 📖 概述

Cookie 自动刷新功能为闲鱼自动回复系统提供了智能的 Cookie 管理能力，能够自动检测 Cookie 有效性并进行刷新，确保系统长期稳定运行。

## 🚀 快速开始

### 1. 启用功能

在 `global_config.yml` 中配置：

```yaml
COOKIE_AUTO_UPDATE:
  enabled: true # 启用Cookie自动更新
  refresh_interval: 3600 # 刷新间隔（秒），默认1小时
  retry_interval: 300 # 重试间隔（秒），默认5分钟
  batch_size: 5 # 批量处理大小
  timeout: 30 # 请求超时时间（秒）
  max_retries: 3 # 最大重试次数
  enable_notifications: true # 启用通知
```

### 2. 启动系统

```bash
cd xianyu-auto-reply
python Start.py
```

系统启动时会自动初始化 Cookie 自动更新服务。

## ⚙️ 配置详解

### 核心配置项

| 配置项                 | 类型    | 默认值 | 说明                         |
| ---------------------- | ------- | ------ | ---------------------------- |
| `enabled`              | boolean | true   | 是否启用 Cookie 自动更新功能 |
| `refresh_interval`     | int     | 3600   | Cookie 刷新检查间隔（秒）    |
| `retry_interval`       | int     | 300    | 失败重试间隔（秒）           |
| `batch_size`           | int     | 5      | 批量处理的 Cookie 数量       |
| `timeout`              | int     | 30     | HTTP 请求超时时间（秒）      |
| `max_retries`          | int     | 3      | 单个 Cookie 最大重试次数     |
| `enable_notifications` | boolean | true   | 是否启用更新通知             |

### 高级配置

```yaml
COOKIE_AUTO_UPDATE:
  # 基础配置
  enabled: true
  refresh_interval: 3600

  # 性能配置
  batch_size: 10 # 增加批量处理数量
  concurrent_limit: 3 # 并发处理限制

  # 重试策略
  max_retries: 5 # 增加重试次数
  retry_backoff: 2 # 重试退避倍数

  # 监控配置
  health_check_interval: 600 # 健康检查间隔
  log_level: 'INFO' # 日志级别
```

## 🔌 API 接口使用

### 1. 获取自动更新状态

```http
GET /cookie-auto-update/status
```

**响应示例：**

```json
{
  "enabled": true,
  "total_accounts": 5,
  "active_tasks": 3,
  "last_update": "2025-09-13T22:00:00Z",
  "accounts": {
    "account_001": {
      "status": "active",
      "last_refresh": "2025-09-13T21:30:00Z",
      "next_refresh": "2025-09-13T22:30:00Z"
    }
  }
}
```

### 2. 启用账号自动更新

```http
POST /cookie-auto-update/enable
Content-Type: application/json

{
  "cookie_id": "account_001"
}
```

### 3. 禁用账号自动更新

```http
POST /cookie-auto-update/disable
Content-Type: application/json

{
  "cookie_id": "account_001"
}
```

### 4. 强制刷新 Cookie

```http
POST /cookie-auto-update/force-update
Content-Type: application/json

{
  "cookie_id": "account_001"
}
```

### 5. 批量更新 Cookie

```http
POST /cookie-auto-update/batch-update
Content-Type: application/json

{
  "cookie_ids": ["account_001", "account_002", "account_003"]
}
```

## 🛠️ 编程接口使用

### Python 代码示例

```python
import asyncio
from cookie_manager import CookieManager

async def main():
    # 创建Cookie管理器
    loop = asyncio.get_event_loop()
    manager = CookieManager(loop)

    # 启用自动更新
    success = manager.enable_cookie_auto_update("account_001")
    print(f"启用结果: {success}")

    # 检查更新状态
    status = manager.get_cookie_auto_update_status()
    print(f"更新状态: {status}")

    # 获取Cookie Token
    token = manager.get_cookie_token("account_001")
    print(f"Cookie Token: {token}")

    # 验证Token有效性
    is_valid = manager.is_cookie_token_valid("account_001")
    print(f"Token有效: {is_valid}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 直接使用自动更新器

```python
from utils.cookie_auto_updater import cookie_auto_updater

# 启动账号自动更新
cookie_auto_updater.start_account_auto_update(
    cookie_id="account_001",
    cookie_value="your_cookie_value",
    device_id="your_device_id"
)

# 停止账号自动更新
cookie_auto_updater.stop_account_auto_update("account_001")

# 检查更新状态
status = cookie_auto_updater.get_update_status()
print(status)
```

## 📊 监控和日志

### 日志位置

- **应用日志**: `logs/app.log`
- **Cookie 更新日志**: `logs/cookie_update.log`
- **错误日志**: `logs/error.log`

### 关键日志示例

```
2025-09-13 22:00:00 | INFO | Cookie自动更新器初始化完成 - 启用状态: True, 刷新间隔: 3600秒
2025-09-13 22:00:01 | INFO | 账号 account_001 自动更新任务已启动
2025-09-13 22:30:00 | INFO | 开始检查账号 account_001 的Cookie有效性
2025-09-13 22:30:01 | INFO | 账号 account_001 Cookie刷新成功
```

### 监控指标

通过 API 可以获取以下监控指标：

- 总账号数量
- 活跃更新任务数
- 最后更新时间
- 成功/失败统计
- 平均响应时间

## 🚨 故障排除

### 常见问题

#### 1. Cookie 更新失败

**症状**: 日志显示"Cookie 更新失败"

**解决方案**:

```bash
# 检查网络连接
curl -I https://h5api.m.taobao.com

# 检查Cookie格式
# 确保Cookie包含必要的字段：_m_h5_tk, _m_h5_tk_enc

# 重启服务
python Start.py
```

#### 2. 自动更新未启动

**症状**: 系统启动后没有自动更新任务

**解决方案**:

```yaml
# 检查配置文件
COOKIE_AUTO_UPDATE:
  enabled: true # 确保为true

# 检查数据库中的Cookie记录
# 确保Cookie已正确保存
```

#### 3. 更新频率过高

**症状**: 系统频繁进行 Cookie 更新

**解决方案**:

```yaml
# 调整刷新间隔
COOKIE_AUTO_UPDATE:
  refresh_interval: 7200 # 增加到2小时
  retry_interval: 600 # 增加重试间隔
```

### 调试模式

启用详细日志：

```yaml
COOKIE_AUTO_UPDATE:
  log_level: 'DEBUG'
```

或通过环境变量：

```bash
export COOKIE_UPDATE_LOG_LEVEL=DEBUG
python Start.py
```

## 🔧 高级用法

### 自定义更新策略

```python
from utils.cookie_auto_updater import CookieAutoUpdater

class CustomCookieUpdater(CookieAutoUpdater):
    async def custom_update_strategy(self, cookie_id: str):
        """自定义更新策略"""
        # 检查业务时间
        current_hour = datetime.now().hour
        if 2 <= current_hour <= 6:  # 凌晨2-6点暂停更新
            return False

        # 检查账号活跃度
        if self.is_account_inactive(cookie_id):
            return False

        return await self.update_cookie(cookie_id)
```

### 集成外部监控

```python
import requests

def send_alert(message: str):
    """发送告警到外部系统"""
    webhook_url = "https://your-webhook-url.com"
    payload = {
        "text": f"Cookie更新告警: {message}",
        "timestamp": datetime.now().isoformat()
    }
    requests.post(webhook_url, json=payload)

# 在更新失败时调用
cookie_auto_updater.on_update_failed = send_alert
```

## 📈 性能优化

### 1. 批量处理优化

```yaml
COOKIE_AUTO_UPDATE:
  batch_size: 20 # 增加批量大小
  concurrent_limit: 5 # 控制并发数
  batch_delay: 1 # 批次间延迟
```

### 2. 内存优化

```python
# 定期清理过期数据
cookie_auto_updater.cleanup_expired_tokens()

# 限制内存使用
import resource
resource.setrlimit(resource.RLIMIT_AS, (1024*1024*512, -1))  # 512MB
```

### 3. 网络优化

```yaml
COOKIE_AUTO_UPDATE:
  timeout: 15 # 减少超时时间
  connection_pool_size: 10 # 连接池大小
  keep_alive: true # 启用连接复用
```

## 🔒 安全注意事项

### 1. Cookie 安全

- Cookie 数据加密存储
- 定期轮换加密密钥
- 限制 Cookie 访问权限

### 2. API 安全

```python
# 添加API认证
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/cookie-auto-update/"):
        token = request.headers.get("Authorization")
        if not verify_token(token):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return await call_next(request)
```

### 3. 日志安全

```yaml
# 避免在日志中记录敏感信息
COOKIE_AUTO_UPDATE:
  log_sensitive_data: false
  mask_cookie_values: true
```

## 📚 最佳实践

### 1. 部署建议

- 使用进程管理器（如 supervisor）
- 配置日志轮转
- 设置健康检查
- 准备回滚方案

### 2. 监控建议

- 监控 Cookie 更新成功率
- 设置响应时间告警
- 监控系统资源使用
- 定期检查日志异常

### 3. 维护建议

- 定期备份配置和数据
- 更新依赖包版本
- 清理过期日志文件
- 优化数据库性能

## 🆘 技术支持

如果遇到问题，请按以下步骤操作：

1. **检查日志**: 查看详细错误信息
2. **验证配置**: 确认配置文件正确
3. **测试网络**: 确保网络连接正常
4. **重启服务**: 尝试重启应用
5. **联系支持**: 提供详细的错误日志

---

**版本**: v1.0.0  
**更新时间**: 2025-09-13  
**兼容性**: Python 3.8+, FastAPI 0.68+
