# Cookie 自动更新 API 参考文档

## 🌐 API 概述

Cookie 自动更新功能提供了完整的 RESTful API 接口，支持对 Cookie 自动刷新功能的全面管理和监控。

**基础 URL**: `http://localhost:8000` (默认)

## 🔐 认证

所有 API 请求都需要包含认证头：

```http
Authorization: Bearer your_api_token
Content-Type: application/json
```

## 📋 API 端点列表

### 1. 获取自动更新状态

获取 Cookie 自动更新功能的整体状态信息。

**端点**: `GET /cookie-auto-update/status`

**请求示例**:

```bash
curl -X GET "http://localhost:8000/cookie-auto-update/status" \
  -H "Authorization: Bearer your_token"
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "enabled": true,
    "total_accounts": 5,
    "active_tasks": 3,
    "failed_tasks": 0,
    "last_update": "2025-09-13T22:00:00Z",
    "next_batch_update": "2025-09-13T23:00:00Z",
    "statistics": {
      "total_updates_today": 24,
      "successful_updates": 22,
      "failed_updates": 2,
      "average_response_time": 1.2
    },
    "accounts": {
      "account_001": {
        "status": "active",
        "last_refresh": "2025-09-13T21:30:00Z",
        "next_refresh": "2025-09-13T22:30:00Z",
        "success_count": 10,
        "failure_count": 0
      },
      "account_002": {
        "status": "paused",
        "last_refresh": "2025-09-13T20:00:00Z",
        "next_refresh": null,
        "success_count": 8,
        "failure_count": 2
      }
    }
  }
}
```

**响应字段说明**:

| 字段             | 类型    | 说明                    |
| ---------------- | ------- | ----------------------- |
| `enabled`        | boolean | 自动更新功能是否启用    |
| `total_accounts` | integer | 总账号数量              |
| `active_tasks`   | integer | 活跃的更新任务数        |
| `failed_tasks`   | integer | 失败的任务数            |
| `last_update`    | string  | 最后更新时间 (ISO 8601) |
| `statistics`     | object  | 统计信息                |
| `accounts`       | object  | 各账号详细状态          |

### 2. 启用账号自动更新

为指定账号启用 Cookie 自动更新功能。

**端点**: `POST /cookie-auto-update/enable`

**请求体**:

```json
{
  "cookie_id": "account_001",
  "options": {
    "refresh_interval": 3600,
    "max_retries": 3,
    "enable_notifications": true
  }
}
```

**请求示例**:

```bash
curl -X POST "http://localhost:8000/cookie-auto-update/enable" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "cookie_id": "account_001",
    "options": {
      "refresh_interval": 3600
    }
  }'
```

**响应示例**:

```json
{
  "success": true,
  "message": "账号 account_001 自动更新已启用",
  "data": {
    "cookie_id": "account_001",
    "status": "enabled",
    "next_refresh": "2025-09-13T23:00:00Z",
    "settings": {
      "refresh_interval": 3600,
      "max_retries": 3,
      "enable_notifications": true
    }
  }
}
```

**错误响应**:

```json
{
  "success": false,
  "error": "ACCOUNT_NOT_FOUND",
  "message": "账号 account_001 不存在",
  "code": 404
}
```

### 3. 禁用账号自动更新

为指定账号禁用 Cookie 自动更新功能。

**端点**: `POST /cookie-auto-update/disable`

**请求体**:

```json
{
  "cookie_id": "account_001",
  "reason": "manual_disable"
}
```

**响应示例**:

```json
{
  "success": true,
  "message": "账号 account_001 自动更新已禁用",
  "data": {
    "cookie_id": "account_001",
    "status": "disabled",
    "disabled_at": "2025-09-13T22:00:00Z",
    "reason": "manual_disable"
  }
}
```

### 4. 强制刷新 Cookie

立即强制刷新指定账号的 Cookie。

**端点**: `POST /cookie-auto-update/force-update`

**请求体**:

```json
{
  "cookie_id": "account_001",
  "skip_validation": false
}
```

**响应示例**:

```json
{
  "success": true,
  "message": "账号 account_001 Cookie强制更新成功",
  "data": {
    "cookie_id": "account_001",
    "update_time": "2025-09-13T22:00:00Z",
    "old_token": "abc123...",
    "new_token": "def456...",
    "response_time": 1.2,
    "next_scheduled_update": "2025-09-13T23:00:00Z"
  }
}
```

**错误响应**:

```json
{
  "success": false,
  "error": "UPDATE_FAILED",
  "message": "Cookie更新失败: 网络超时",
  "data": {
    "cookie_id": "account_001",
    "error_code": "NETWORK_TIMEOUT",
    "retry_count": 2,
    "next_retry": "2025-09-13T22:05:00Z"
  }
}
```

### 5. 批量更新 Cookie

批量更新多个账号的 Cookie。

**端点**: `POST /cookie-auto-update/batch-update`

**请求体**:

```json
{
  "cookie_ids": ["account_001", "account_002", "account_003"],
  "options": {
    "concurrent_limit": 3,
    "timeout": 30,
    "skip_failed": true
  }
}
```

**响应示例**:

```json
{
  "success": true,
  "message": "批量更新完成",
  "data": {
    "total_requested": 3,
    "successful": 2,
    "failed": 1,
    "results": [
      {
        "cookie_id": "account_001",
        "status": "success",
        "update_time": "2025-09-13T22:00:00Z",
        "response_time": 1.1
      },
      {
        "cookie_id": "account_002",
        "status": "success",
        "update_time": "2025-09-13T22:00:01Z",
        "response_time": 1.3
      },
      {
        "cookie_id": "account_003",
        "status": "failed",
        "error": "INVALID_COOKIE",
        "message": "Cookie格式无效"
      }
    ],
    "execution_time": 2.5
  }
}
```

### 6. 获取账号详细信息

获取指定账号的详细更新信息。

**端点**: `GET /cookie-auto-update/account/{cookie_id}`

**响应示例**:

```json
{
  "success": true,
  "data": {
    "cookie_id": "account_001",
    "status": "active",
    "created_at": "2025-09-10T10:00:00Z",
    "last_refresh": "2025-09-13T21:30:00Z",
    "next_refresh": "2025-09-13T22:30:00Z",
    "settings": {
      "refresh_interval": 3600,
      "max_retries": 3,
      "enable_notifications": true
    },
    "statistics": {
      "total_updates": 50,
      "successful_updates": 48,
      "failed_updates": 2,
      "average_response_time": 1.1,
      "last_7_days": {
        "updates": 14,
        "success_rate": 0.96
      }
    },
    "recent_updates": [
      {
        "timestamp": "2025-09-13T21:30:00Z",
        "status": "success",
        "response_time": 1.2,
        "token_changed": true
      },
      {
        "timestamp": "2025-09-13T20:30:00Z",
        "status": "success",
        "response_time": 0.9,
        "token_changed": false
      }
    ]
  }
}
```

### 7. 更新账号设置

更新指定账号的自动更新设置。

**端点**: `PUT /cookie-auto-update/account/{cookie_id}/settings`

**请求体**:

```json
{
  "refresh_interval": 7200,
  "max_retries": 5,
  "enable_notifications": false,
  "custom_headers": {
    "User-Agent": "custom-agent"
  }
}
```

**响应示例**:

```json
{
  "success": true,
  "message": "账号设置更新成功",
  "data": {
    "cookie_id": "account_001",
    "old_settings": {
      "refresh_interval": 3600,
      "max_retries": 3
    },
    "new_settings": {
      "refresh_interval": 7200,
      "max_retries": 5,
      "enable_notifications": false
    },
    "updated_at": "2025-09-13T22:00:00Z"
  }
}
```

### 8. 获取更新历史

获取系统的更新历史记录。

**端点**: `GET /cookie-auto-update/history`

**查询参数**:

- `cookie_id` (可选): 指定账号 ID
- `start_date` (可选): 开始日期 (YYYY-MM-DD)
- `end_date` (可选): 结束日期 (YYYY-MM-DD)
- `status` (可选): 状态筛选 (success/failed)
- `limit` (可选): 返回记录数限制 (默认 100)
- `offset` (可选): 偏移量 (默认 0)

**请求示例**:

```bash
curl -X GET "http://localhost:8000/cookie-auto-update/history?cookie_id=account_001&limit=10" \
  -H "Authorization: Bearer your_token"
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "total": 150,
    "limit": 10,
    "offset": 0,
    "records": [
      {
        "id": "update_001",
        "cookie_id": "account_001",
        "timestamp": "2025-09-13T21:30:00Z",
        "status": "success",
        "response_time": 1.2,
        "token_changed": true,
        "old_token_hash": "abc123...",
        "new_token_hash": "def456...",
        "user_agent": "Mozilla/5.0...",
        "ip_address": "192.168.1.100"
      }
    ]
  }
}
```

### 9. 系统健康检查

检查 Cookie 自动更新系统的健康状态。

**端点**: `GET /cookie-auto-update/health`

**响应示例**:

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2025-09-13T22:00:00Z",
    "uptime": 86400,
    "version": "1.0.0",
    "components": {
      "database": {
        "status": "healthy",
        "response_time": 0.05
      },
      "scheduler": {
        "status": "healthy",
        "active_jobs": 5
      },
      "http_client": {
        "status": "healthy",
        "connection_pool": "10/20"
      }
    },
    "metrics": {
      "memory_usage": "45%",
      "cpu_usage": "12%",
      "disk_usage": "30%"
    }
  }
}
```

## 🚨 错误代码

| 错误代码            | HTTP 状态码 | 说明            |
| ------------------- | ----------- | --------------- |
| `ACCOUNT_NOT_FOUND` | 404         | 账号不存在      |
| `INVALID_COOKIE`    | 400         | Cookie 格式无效 |
| `UPDATE_FAILED`     | 500         | 更新失败        |
| `NETWORK_TIMEOUT`   | 408         | 网络超时        |
| `RATE_LIMITED`      | 429         | 请求频率限制    |
| `UNAUTHORIZED`      | 401         | 未授权访问      |
| `FORBIDDEN`         | 403         | 禁止访问        |
| `INTERNAL_ERROR`    | 500         | 内部服务器错误  |

## 📊 响应格式

所有 API 响应都遵循统一格式：

**成功响应**:

```json
{
  "success": true,
  "message": "操作成功",
  "data": { ... },
  "timestamp": "2025-09-13T22:00:00Z"
}
```

**错误响应**:

```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "错误描述",
  "code": 400,
  "timestamp": "2025-09-13T22:00:00Z",
  "details": { ... }
}
```

## 🔄 Webhook 通知

系统支持 Webhook 通知，在重要事件发生时主动推送消息。

### 配置 Webhook

```yaml
COOKIE_AUTO_UPDATE:
  webhooks:
    - url: 'https://your-webhook-url.com/cookie-update'
      events: ['update_success', 'update_failed', 'account_disabled']
      secret: 'your_webhook_secret'
```

### Webhook 负载示例

```json
{
  "event": "update_success",
  "timestamp": "2025-09-13T22:00:00Z",
  "data": {
    "cookie_id": "account_001",
    "update_time": "2025-09-13T22:00:00Z",
    "response_time": 1.2,
    "token_changed": true
  },
  "signature": "sha256=abc123..."
}
```

## 📈 使用限制

| 限制类型 | 默认值    | 说明                   |
| -------- | --------- | ---------------------- |
| 请求频率 | 100/分钟  | 每分钟最大请求数       |
| 批量操作 | 50 个账号 | 单次批量操作最大账号数 |
| 并发连接 | 10 个     | 最大并发连接数         |
| 响应大小 | 10MB      | 最大响应体大小         |

## 🛠️ SDK 示例

### Python SDK

```python
import requests
import json

class CookieAutoUpdateClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    def get_status(self):
        """获取自动更新状态"""
        response = requests.get(
            f'{self.base_url}/cookie-auto-update/status',
            headers=self.headers
        )
        return response.json()

    def enable_account(self, cookie_id, options=None):
        """启用账号自动更新"""
        data = {'cookie_id': cookie_id}
        if options:
            data['options'] = options

        response = requests.post(
            f'{self.base_url}/cookie-auto-update/enable',
            headers=self.headers,
            json=data
        )
        return response.json()

    def force_update(self, cookie_id):
        """强制更新Cookie"""
        response = requests.post(
            f'{self.base_url}/cookie-auto-update/force-update',
            headers=self.headers,
            json={'cookie_id': cookie_id}
        )
        return response.json()

# 使用示例
client = CookieAutoUpdateClient('http://localhost:8000', 'your_token')
status = client.get_status()
print(json.dumps(status, indent=2))
```

### JavaScript SDK

```javascript
class CookieAutoUpdateClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.headers = {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }

  async getStatus() {
    const response = await fetch(`${this.baseUrl}/cookie-auto-update/status`, {
      headers: this.headers,
    });
    return await response.json();
  }

  async enableAccount(cookieId, options = {}) {
    const response = await fetch(`${this.baseUrl}/cookie-auto-update/enable`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ cookie_id: cookieId, options }),
    });
    return await response.json();
  }

  async forceUpdate(cookieId) {
    const response = await fetch(
      `${this.baseUrl}/cookie-auto-update/force-update`,
      {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({ cookie_id: cookieId }),
      }
    );
    return await response.json();
  }
}

// 使用示例
const client = new CookieAutoUpdateClient(
  'http://localhost:8000',
  'your_token'
);
client.getStatus().then((status) => console.log(status));
```

---

**版本**: v1.0.0  
**更新时间**: 2025-09-13  
**联系方式**: 技术支持团队
