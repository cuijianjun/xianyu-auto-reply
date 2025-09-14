import sqlite3
import threading
import os
import logging
import json
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import io
import base64

# 配置日志
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path='data/xianyu_auto_reply.db', sql_log_level='INFO'):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
            sql_log_level: SQL日志级别 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self.conn = None
        self.sql_log_level = getattr(logging, sql_log_level.upper(), logging.INFO)
        
        # 确保数据目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, mode=0o755, exist_ok=True)
                logger.info(f"成功创建数据目录: {db_dir}")
            except PermissionError as e:
                logger.error(f"创建数据目录失败，权限不足: {e}")
                logger.warning(f"使用当前目录作为数据库路径: {db_path}")
            except Exception as e:
                logger.error(f"创建数据目录失败: {e}")
                # 目录不存在，尝试创建
                try:
                    os.makedirs(db_dir, exist_ok=True)
                    logger.info(f"成功创建数据目录: {db_dir}")
                except PermissionError:
                    logger.error(f"无权限创建数据目录: {db_dir}")
                    logger.warning(f"使用当前目录作为数据库路径: {db_path}")
                except Exception as e:
                    logger.error(f"创建数据目录失败: {db_dir}, 错误: {e}")
        
        logger.info(f"SQL日志已启用，日志级别: {self.sql_log_level}")

        self.init_db()
    
    def init_db(self):
        """初始化数据库表结构"""
        with self.lock:
            try:
                self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
                cursor = self.conn.cursor()
                
                # 创建用户表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')

                # 创建邮箱验证码表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    code TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')

                # 创建图形验证码表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS captcha_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    code TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')

                # 创建cookies表（添加user_id字段和auto_confirm字段）
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS cookies (
                    id TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    auto_confirm INTEGER DEFAULT 1,
                    remark TEXT DEFAULT '',
                    pause_duration INTEGER DEFAULT 10,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                ''')

                # 创建keywords表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS keywords (
                    cookie_id TEXT,
                    keyword TEXT,
                    reply TEXT,
                    item_id TEXT,
                    type TEXT DEFAULT 'text',
                    image_url TEXT,
                    FOREIGN KEY (cookie_id) REFERENCES cookies(id) ON DELETE CASCADE
                )
                ''')

                # 创建cookie_status表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS cookie_status (
                    cookie_id TEXT PRIMARY KEY,
                    enabled BOOLEAN DEFAULT TRUE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cookie_id) REFERENCES cookies(id) ON DELETE CASCADE
                )
                ''')

                # 创建系统设置表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')

                # 创建邮箱验证码表（新版本）
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_verification_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    code TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'register',
                    used BOOLEAN DEFAULT FALSE,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')

                # 创建用户设置表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                ''')

                # 创建AI回复设置表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_reply_settings (
                    cookie_id TEXT PRIMARY KEY,
                    ai_enabled BOOLEAN DEFAULT FALSE,
                    model_name TEXT DEFAULT 'qwen-plus',
                    api_key TEXT DEFAULT '',
                    base_url TEXT DEFAULT 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                    max_tokens INTEGER DEFAULT 100,
                    temperature REAL DEFAULT 0.7,
                    max_bargain_rounds INTEGER DEFAULT 3,
                    max_discount_percent REAL DEFAULT 15.0,
                    max_discount_amount REAL DEFAULT 50.0,
                    custom_prompts TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cookie_id) REFERENCES cookies(id) ON DELETE CASCADE
                )
                ''')

                # 创建AI对话历史表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cookie_id TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    intent_type TEXT DEFAULT 'default',
                    bargain_round INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cookie_id) REFERENCES cookies(id) ON DELETE CASCADE
                )
                ''')

                # 创建消息日志表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cookie_id TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    message_content TEXT NOT NULL,
                    sender_type TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cookie_id) REFERENCES cookies(id) ON DELETE CASCADE
                )
                ''')

                # 创建商品信息缓存表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS item_info (
                    item_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    price REAL DEFAULT 0,
                    description TEXT DEFAULT '',
                    images TEXT DEFAULT '[]',
                    seller_id TEXT DEFAULT '',
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')

                # 创建默认回复表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS default_replies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cookie_id TEXT NOT NULL,
                    reply_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cookie_id) REFERENCES cookies(id) ON DELETE CASCADE
                )
                ''')

                # 创建消息通知表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cookie_id TEXT NOT NULL,
                    channel_id INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cookie_id) REFERENCES cookies(id) ON DELETE CASCADE,
                    FOREIGN KEY (channel_id) REFERENCES notification_channels(id) ON DELETE CASCADE,
                    UNIQUE(cookie_id, channel_id)
                )
                ''')

                # 创建订单表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE NOT NULL,
                    cookie_id TEXT NOT NULL,
                    buyer_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    item_title TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending',
                    auto_confirm BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cookie_id) REFERENCES cookies(id) ON DELETE CASCADE
                )
                ''')

                # 创建通知渠道表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    config TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                ''')

                # 创建卡券表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    api_config TEXT DEFAULT '{}',
                    text_content TEXT DEFAULT '',
                    data_content TEXT DEFAULT '',
                    image_url TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    enabled BOOLEAN DEFAULT TRUE,
                    delay_seconds INTEGER DEFAULT 0,
                    is_multi_spec BOOLEAN DEFAULT FALSE,
                    spec_name TEXT DEFAULT '',
                    spec_value TEXT DEFAULT '',
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                ''')

                # 创建自动发货规则表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS delivery_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    card_id INTEGER NOT NULL,
                    delivery_count INTEGER DEFAULT 1,
                    enabled BOOLEAN DEFAULT TRUE,
                    description TEXT DEFAULT '',
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                ''')

                # 创建索引以提高查询性能
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_cookies_user_id ON cookies(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_keywords_cookie_id ON keywords(cookie_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_conversations_cookie_id ON ai_conversations(cookie_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_conversations_chat_id ON ai_conversations(chat_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_logs_cookie_id ON message_logs(cookie_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_logs_chat_id ON message_logs(chat_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_cookie_id ON orders(cookie_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')

                # 检查并创建默认管理员用户
                self._create_default_admin_user(cursor)
                
                # 设置默认系统配置
                self._set_default_system_settings(cursor)
                
                self.conn.commit()
                logger.info("数据库初始化完成")
            except Exception as e:
                logger.error(f"数据库初始化失败: {e}")
                if self.conn:
                    self.conn.rollback()
                raise

    def _execute_sql(self, cursor, sql, params=None):
        """执行SQL语句并记录日志"""
        if logger.isEnabledFor(self.sql_log_level):
            logger.log(self.sql_log_level, f"执行SQL: {sql}")
            if params:
                logger.log(self.sql_log_level, f"参数: {params}")
        
        if params:
            return cursor.execute(sql, params)
        else:
            return cursor.execute(sql)

    def save_cookie(self, cookie_id, cookie_value, user_id=1):
        """保存Cookie"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                self._execute_sql(cursor, '''
                    INSERT OR REPLACE INTO cookies (id, cookie, user_id, created_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (cookie_id, cookie_value, user_id))
                self.conn.commit()
                logger.info(f"Cookie保存成功: {cookie_id}")
                return True
            except Exception as e:
                logger.error(f"Cookie保存失败: {e}")
                return False

    def get_cookie(self, cookie_id):
        """获取Cookie"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                self._execute_sql(cursor, 'SELECT cookie FROM cookies WHERE id = ?', (cookie_id,))
                result = cursor.fetchone()
                return result[0] if result else None
            except Exception as e:
                logger.error(f"获取Cookie失败: {e}")
                return None

    def get_all_cookies(self, user_id: int = None):
        """获取所有Cookie（支持用户隔离，兼容不同数据库结构）"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                
                # 首先检查表结构，确定正确的列名
                try:
                    cursor.execute("PRAGMA table_info(cookies)")
                    columns = cursor.fetchall()
                    column_names = [col[1] for col in columns]
                    
                    # 确定cookie值的列名
                    cookie_column = 'cookie' if 'cookie' in column_names else 'value'
                    
                    # 构建查询语句
                    if user_id is not None:
                        query = f"SELECT id, {cookie_column}, user_id FROM cookies WHERE user_id = ?"
                        self._execute_sql(cursor, query, (user_id,))
                    else:
                        query = f"SELECT id, {cookie_column}, user_id FROM cookies"
                        self._execute_sql(cursor, query)
                    
                    # 返回列表格式，兼容 reply_server.py 的期望
                    results = []
                    for row in cursor.fetchall():
                        cookie_dict = {
                            'id': row[0],
                            'cookie': row[1],  # 统一使用 'cookie' 作为键名
                            'user_id': row[2] if len(row) > 2 else user_id
                        }
                        results.append(cookie_dict)
                    
                    return results
                    
                except Exception as schema_error:
                    # 如果检查表结构失败，尝试使用默认的 cookie 列名
                    logger.warning(f"检查表结构失败，使用默认列名: {schema_error}")
                    if user_id is not None:
                        self._execute_sql(cursor, "SELECT id, cookie FROM cookies WHERE user_id = ?", (user_id,))
                    else:
                        self._execute_sql(cursor, "SELECT id, cookie FROM cookies")
                    return {row[0]: row[1] for row in cursor.fetchall()}
                    
            except Exception as e:
                logger.error(f"获取所有Cookie失败: {e}")
                return [] if isinstance(e, Exception) and "column" in str(e).lower() else {}

    def delete_cookie(self, cookie_id):
        """删除Cookie"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                self._execute_sql(cursor, 'DELETE FROM cookies WHERE id = ?', (cookie_id,))
                self.conn.commit()
                logger.info(f"Cookie删除成功: {cookie_id}")
                return True
            except Exception as e:
                logger.error(f"Cookie删除失败: {e}")
                return False

    def get_user_by_username(self, username: str):
        """根据用户名获取用户信息"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                self._execute_sql(cursor, '''
                SELECT id, username, email, password_hash, is_active, created_at, updated_at
                FROM users WHERE username = ?
                ''', (username,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'username': row[1],
                        'email': row[2],
                        'password_hash': row[3],
                        'is_active': bool(row[4]),
                        'created_at': row[5],
                        'updated_at': row[6]
                    }
                return None
            except Exception as e:
                logger.error(f"获取用户信息失败: {e}")
                return None

    def get_user_by_email(self, email: str):
        """根据邮箱获取用户信息"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                self._execute_sql(cursor, '''
                SELECT id, username, email, password_hash, is_active, created_at, updated_at
                FROM users WHERE email = ?
                ''', (email,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'username': row[1],
                        'email': row[2],
                        'password_hash': row[3],
                        'is_active': bool(row[4]),
                        'created_at': row[5],
                        'updated_at': row[6]
                    }
                return None
            except Exception as e:
                logger.error(f"获取用户信息失败: {e}")
                return None

    def verify_user_password(self, username: str, password: str) -> bool:
        """验证用户密码"""
        user = self.get_user_by_username(username)
        if not user:
            return False

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return user['password_hash'] == password_hash and user['is_active']

    def verify_email_code(self, email: str, code: str, code_type: str = 'register') -> bool:
        """验证邮箱验证码"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                self._execute_sql(cursor, '''
                SELECT id FROM email_verification_codes 
                WHERE email = ? AND code = ? AND type = ? AND used = 0 
                AND expires_at > CURRENT_TIMESTAMP
                ''', (email, code, code_type))
                
                row = cursor.fetchone()
                if row:
                    # 标记验证码为已使用
                    self._execute_sql(cursor, '''
                    UPDATE email_verification_codes 
                    SET used = 1, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                    ''', (row[0],))
                    self.conn.commit()
                    return True
                return False
            except Exception as e:
                logger.error(f"验证邮箱验证码失败: {e}")
                return False

    def get_system_setting(self, key: str, default_value: str = None) -> str:
        """获取系统设置"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                self._execute_sql(cursor, 'SELECT value FROM system_settings WHERE key = ?', (key,))
                row = cursor.fetchone()
                return row[0] if row else default_value
            except Exception as e:
                logger.error(f"获取系统设置失败: {e}")
                return default_value

    def set_system_setting(self, key: str, value: str, description: str = '') -> bool:
        """设置系统设置"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                self._execute_sql(cursor, '''
                INSERT OR REPLACE INTO system_settings (key, value, description, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (key, value, description))
                self.conn.commit()
                return True
            except Exception as e:
                logger.error(f"设置系统设置失败: {e}")
                return False

    def get_cookie_details(self, cookie_id: str):
        """获取Cookie的详细信息，包括user_id、auto_confirm、remark和pause_duration"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                self._execute_sql(cursor, "SELECT id, cookie, user_id, auto_confirm, remark, pause_duration, created_at FROM cookies WHERE id = ?", (cookie_id,))
                result = cursor.fetchone()
                if result:
                    return {
                        'id': result[0],
                        'value': result[1],
                        'user_id': result[2],
                        'auto_confirm': bool(result[3]),
                        'remark': result[4] or '',
                        'pause_duration': result[5] if result[5] is not None else 10,
                        'created_at': result[6]
                    }
                return None
            except Exception as e:
                logger.error(f"获取Cookie详细信息失败: {e}")
                return None

    def get_user_settings(self, user_id: int):
        """获取用户的所有设置"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute('''
                SELECT key, value, description, updated_at
                FROM user_settings
                WHERE user_id = ?
                ORDER BY key
                ''', (user_id,))

                settings = {}
                for row in cursor.fetchall():
                    settings[row[0]] = {
                        'value': row[1],
                        'description': row[2],
                        'updated_at': row[3]
                    }

                return settings
            except Exception as e:
                logger.error(f"获取用户设置失败: {e}")
                return {}

    def get_user_setting(self, user_id: int, key: str):
        """获取用户的特定设置"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute('''
                SELECT value, description, updated_at
                FROM user_settings
                WHERE user_id = ? AND key = ?
                ''', (user_id, key))

                row = cursor.fetchone()
                if row:
                    return {
                        'key': key,
                        'value': row[0],
                        'description': row[1],
                        'updated_at': row[2]
                    }
                return None
            except Exception as e:
                logger.error(f"获取用户设置失败: {e}")
                return None

    def set_user_setting(self, user_id: int, key: str, value: str, description: str = None):
        """设置用户配置"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute('''
                INSERT OR REPLACE INTO user_settings (user_id, key, value, description, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, key, value, description))

                self.conn.commit()
                logger.info(f"用户设置更新成功: user_id={user_id}, key={key}")
                return True
            except Exception as e:
                logger.error(f"设置用户配置失败: {e}")
                self.conn.rollback()
                return False

    def get_auto_confirm(self, cookie_id: str) -> bool:
        """获取Cookie的自动确认发货设置"""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                self._execute_sql(cursor, "SELECT auto_confirm FROM cookies WHERE id = ?", (cookie_id,))
                result = cursor.fetchone()
                return bool(result[0]) if result else False
            except Exception as e:
                logger.error(f"获取自动确认发货设置失败: {e}")
                return False

    def _create_default_admin_user(self, cursor):
        """创建默认管理员用户"""
        try:
            # 检查是否已存在管理员用户
            self._execute_sql(cursor, "SELECT id FROM users WHERE username = ?", ('admin',))
            if cursor.fetchone():
                logger.info("管理员用户已存在，跳过创建")
                return

            # 创建默认管理员用户
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
            password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
            
            self._execute_sql(cursor, '''
                INSERT INTO users (username, email, password_hash, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', ('admin', 'admin@example.com', password_hash, True))
            
            logger.info("默认管理员用户创建成功 (用户名: admin)")
        except Exception as e:
            logger.error(f"创建默认管理员用户失败: {e}")

    def _set_default_system_settings(self, cursor):
        """设置默认系统配置"""
        try:
            default_settings = {
                'system_initialized': 'true',
                'auto_reply_enabled': os.getenv('AUTO_REPLY_ENABLED', 'true'),
                'ai_reply_enabled': os.getenv('AI_REPLY_ENABLED', 'false'),
                'multiuser_enabled': os.getenv('MULTIUSER_ENABLED', 'true'),
                'user_registration_enabled': os.getenv('USER_REGISTRATION_ENABLED', 'true'),
                'email_verification_enabled': os.getenv('EMAIL_VERIFICATION_ENABLED', 'true'),
                'captcha_enabled': os.getenv('CAPTCHA_ENABLED', 'true'),
                'version': '1.0.0'
            }
            
            for key, value in default_settings.items():
                # 检查设置是否已存在
                self._execute_sql(cursor, "SELECT value FROM system_settings WHERE key = ?", (key,))
                if not cursor.fetchone():
                    self._execute_sql(cursor, '''
                        INSERT INTO system_settings (key, value, description, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (key, value, f'默认{key}设置'))
            
            logger.info("默认系统配置设置完成")
        except Exception as e:
            logger.error(f"设置默认系统配置失败: {e}")

    def save_ai_reply_settings(self, cookie_id: str, settings: dict) -> bool:
        """保存AI回复设置"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    INSERT OR REPLACE INTO ai_reply_settings
                    (cookie_id, ai_enabled, model_name, api_key, base_url,
                     max_tokens, temperature, max_bargain_rounds, max_discount_percent,
                     max_discount_amount, custom_prompts, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    cookie_id,
                    settings.get('ai_enabled', False),
                    settings.get('model_name', 'qwen-plus'),
                    settings.get('api_key', ''),
                    settings.get('base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
                    settings.get('max_tokens', 100),
                    settings.get('temperature', 0.7),
                    settings.get('max_bargain_rounds', 3),
                    settings.get('max_discount_percent', 15.0),
                    settings.get('max_discount_amount', 50.0),
                    json.dumps(settings.get('custom_prompts', {}), ensure_ascii=False)
                ))
                
                self.conn.commit()
                logger.info(f"AI回复设置保存成功: {cookie_id}")
                return True
            except Exception as e:
                logger.error(f"保存AI回复设置失败: {e}")
                if self.conn:
                    self.conn.rollback()
                return False

    def get_ai_reply_settings(self, cookie_id: str) -> dict:
        """获取AI回复设置"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    SELECT ai_enabled, model_name, api_key, base_url, max_tokens,
                           temperature, max_bargain_rounds, max_discount_percent,
                           max_discount_amount, custom_prompts
                    FROM ai_reply_settings WHERE cookie_id = ?
                ''', (cookie_id,))
                
                row = cursor.fetchone()
                if row:
                    custom_prompts = {}
                    try:
                        if row[9]:
                            custom_prompts = json.loads(row[9])
                    except json.JSONDecodeError:
                        logger.warning(f"解析自定义提示词失败: {cookie_id}")
                    
                    return {
                        'ai_enabled': bool(row[0]),
                        'model_name': row[1] or 'qwen-plus',
                        'api_key': row[2] or '',
                        'base_url': row[3] or 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                        'max_tokens': row[4] or 100,
                        'temperature': row[5] or 0.7,
                        'max_bargain_rounds': row[6] or 3,
                        'max_discount_percent': row[7] or 15.0,
                        'max_discount_amount': row[8] or 50.0,
                        'custom_prompts': custom_prompts
                    }
                else:
                    # 返回默认设置
                    return {
                        'ai_enabled': False,
                        'model_name': 'qwen-plus',
                        'api_key': '',
                        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                        'max_tokens': 100,
                        'temperature': 0.7,
                        'max_bargain_rounds': 3,
                        'max_discount_percent': 15.0,
                        'max_discount_amount': 50.0,
                        'custom_prompts': {}
                    }
            except Exception as e:
                logger.error(f"获取AI回复设置失败: {e}")
                return {
                    'ai_enabled': False,
                    'model_name': 'qwen-plus',
                    'api_key': '',
                    'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                    'max_tokens': 100,
                    'temperature': 0.7,
                    'max_bargain_rounds': 3,
                    'max_discount_percent': 15.0,
                    'max_discount_amount': 50.0,
                    'custom_prompts': {}
                }

    def get_all_ai_reply_settings(self) -> dict:
        """获取所有账号的AI回复设置"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    SELECT cookie_id, ai_enabled, model_name, api_key, base_url, max_tokens,
                           temperature, max_bargain_rounds, max_discount_percent,
                           max_discount_amount, custom_prompts
                    FROM ai_reply_settings
                ''')
                
                settings = {}
                for row in cursor.fetchall():
                    custom_prompts = {}
                    try:
                        if row[10]:
                            custom_prompts = json.loads(row[10])
                    except json.JSONDecodeError:
                        logger.warning(f"解析自定义提示词失败: {row[0]}")
                    
                    settings[row[0]] = {
                        'ai_enabled': bool(row[1]),
                        'model_name': row[2] or 'qwen-plus',
                        'api_key': row[3] or '',
                        'base_url': row[4] or 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                        'max_tokens': row[5] or 100,
                        'temperature': row[6] or 0.7,
                        'max_bargain_rounds': row[7] or 3,
                        'max_discount_percent': row[8] or 15.0,
                        'max_discount_amount': row[9] or 50.0,
                        'custom_prompts': custom_prompts
                    }
                
                return settings
            except Exception as e:
                logger.error(f"获取所有AI回复设置失败: {e}")
                return {}

    def save_conversation(self, cookie_id: str, chat_id: str, user_message: str, 
                         ai_response: str, intent_type: str = 'default', bargain_round: int = 0) -> bool:
        """保存AI对话记录"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    INSERT INTO ai_conversations 
                    (cookie_id, chat_id, user_message, ai_response, intent_type, bargain_round, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (cookie_id, chat_id, user_message, ai_response, intent_type, bargain_round))
                
                self.conn.commit()
                return True
            except Exception as e:
                logger.error(f"保存对话记录失败: {e}")
                if self.conn:
                    self.conn.rollback()
                return False

    def get_conversation_history(self, cookie_id: str, chat_id: str, limit: int = 10) -> list:
        """获取对话历史"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    SELECT user_message, ai_response, intent_type, bargain_round, created_at
                    FROM ai_conversations 
                    WHERE cookie_id = ? AND chat_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (cookie_id, chat_id, limit))
                
                conversations = []
                for row in cursor.fetchall():
                    conversations.append({
                        'user_message': row[0],
                        'ai_response': row[1],
                        'intent_type': row[2],
                        'bargain_round': row[3],
                        'created_at': row[4]
                    })
                
                return list(reversed(conversations))  # 返回时间正序
            except Exception as e:
                logger.error(f"获取对话历史失败: {e}")
                return []

    def check_database_integrity(self) -> bool:
        """检查数据库完整性"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                # 检查关键表是否存在
                required_tables = [
                    'users', 'cookies', 'keywords', 'cookie_status', 
                    'system_settings', 'user_settings', 'ai_reply_settings',
                    'ai_conversations', 'message_logs', 'item_info',
                    'notification_channels', 'cards', 'delivery_rules'
                ]
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                missing_tables = [table for table in required_tables if table not in existing_tables]
                
                if missing_tables:
                    logger.warning(f"数据库缺少表: {missing_tables}")
                    return False
                
                logger.info("数据库完整性检查通过")
                return True
                
            except Exception as e:
                logger.error(f"数据库完整性检查失败: {e}")
                return False

    # ==================== 通知渠道管理方法 ====================
    
    def get_notification_channels(self, user_id: int) -> list:
        """获取用户的所有通知渠道"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    SELECT id, name, type, config, enabled, created_at, updated_at
                    FROM notification_channels 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                ''', (user_id,))
                
                channels = []
                for row in cursor.fetchall():
                    channels.append({
                        'id': row[0],
                        'name': row[1],
                        'type': row[2],
                        'config': json.loads(row[3]) if row[3] else {},
                        'enabled': bool(row[4]),
                        'created_at': row[5],
                        'updated_at': row[6]
                    })
                
                return channels
            except Exception as e:
                logger.error(f"获取通知渠道失败: {e}")
                return []

    def create_notification_channel(self, name: str, channel_type: str, config: dict, user_id: int) -> int:
        """创建通知渠道"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    INSERT INTO notification_channels (name, type, config, user_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (name, channel_type, json.dumps(config, ensure_ascii=False), user_id))
                
                channel_id = cursor.lastrowid
                self.conn.commit()
                logger.info(f"通知渠道创建成功: {name} (ID: {channel_id})")
                return channel_id
            except Exception as e:
                logger.error(f"创建通知渠道失败: {e}")
                if self.conn:
                    self.conn.rollback()
                raise

    def get_notification_channel(self, channel_id: int) -> dict:
        """获取单个通知渠道"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    SELECT id, name, type, config, enabled, user_id, created_at, updated_at
                    FROM notification_channels 
                    WHERE id = ?
                ''', (channel_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'type': row[2],
                        'config': json.loads(row[3]) if row[3] else {},
                        'enabled': bool(row[4]),
                        'user_id': row[5],
                        'created_at': row[6],
                        'updated_at': row[7]
                    }
                return None
            except Exception as e:
                logger.error(f"获取通知渠道失败: {e}")
                return None

    def update_notification_channel(self, channel_id: int, name: str, config: dict, enabled: bool) -> bool:
        """更新通知渠道"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    UPDATE notification_channels 
                    SET name = ?, config = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (name, json.dumps(config, ensure_ascii=False), enabled, channel_id))
                
                success = cursor.rowcount > 0
                self.conn.commit()
                return success
            except Exception as e:
                logger.error(f"更新通知渠道失败: {e}")
                if self.conn:
                    self.conn.rollback()
                return False

    def delete_notification_channel(self, channel_id: int) -> bool:
        """删除通知渠道"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, 'DELETE FROM notification_channels WHERE id = ?', (channel_id,))
                
                success = cursor.rowcount > 0
                self.conn.commit()
                return success
            except Exception as e:
                logger.error(f"删除通知渠道失败: {e}")
                if self.conn:
                    self.conn.rollback()
                return False

    # ==================== 卡券管理方法 ====================
    
    def get_all_cards(self, user_id: int) -> list:
        """获取用户的所有卡券"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    SELECT id, name, type, api_config, text_content, data_content, 
                           image_url, description, enabled, delay_seconds, is_multi_spec,
                           spec_name, spec_value, created_at, updated_at
                    FROM cards 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                ''', (user_id,))
                
                cards = []
                for row in cursor.fetchall():
                    cards.append({
                        'id': row[0],
                        'name': row[1],
                        'type': row[2],
                        'api_config': json.loads(row[3]) if row[3] else {},
                        'text_content': row[4],
                        'data_content': row[5],
                        'image_url': row[6],
                        'description': row[7],
                        'enabled': bool(row[8]),
                        'delay_seconds': row[9],
                        'is_multi_spec': bool(row[10]),
                        'spec_name': row[11],
                        'spec_value': row[12],
                        'created_at': row[13],
                        'updated_at': row[14]
                    })
                
                return cards
            except Exception as e:
                logger.error(f"获取卡券列表失败: {e}")
                return []

    def create_card(self, name: str, card_type: str, api_config: dict = None, 
                   text_content: str = '', data_content: str = '', image_url: str = '',
                   description: str = '', enabled: bool = True, delay_seconds: int = 0,
                   is_multi_spec: bool = False, spec_name: str = '', spec_value: str = '',
                   user_id: int = 1) -> int:
        """创建卡券"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    INSERT INTO cards (name, type, api_config, text_content, data_content,
                                     image_url, description, enabled, delay_seconds, is_multi_spec,
                                     spec_name, spec_value, user_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (name, card_type, json.dumps(api_config or {}, ensure_ascii=False), 
                      text_content, data_content, image_url, description, enabled, 
                      delay_seconds, is_multi_spec, spec_name, spec_value, user_id))
                
                card_id = cursor.lastrowid
                self.conn.commit()
                logger.info(f"卡券创建成功: {name} (ID: {card_id})")
                return card_id
            except Exception as e:
                logger.error(f"创建卡券失败: {e}")
                if self.conn:
                    self.conn.rollback()
                raise

    def get_card_by_id(self, card_id: int, user_id: int) -> dict:
        """根据ID获取卡券"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    SELECT id, name, type, api_config, text_content, data_content, 
                           image_url, description, enabled, delay_seconds, is_multi_spec,
                           spec_name, spec_value, created_at, updated_at
                    FROM cards 
                    WHERE id = ? AND user_id = ?
                ''', (card_id, user_id))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'type': row[2],
                        'api_config': json.loads(row[3]) if row[3] else {},
                        'text_content': row[4],
                        'data_content': row[5],
                        'image_url': row[6],
                        'description': row[7],
                        'enabled': bool(row[8]),
                        'delay_seconds': row[9],
                        'is_multi_spec': bool(row[10]),
                        'spec_name': row[11],
                        'spec_value': row[12],
                        'created_at': row[13],
                        'updated_at': row[14]
                    }
                return None
            except Exception as e:
                logger.error(f"获取卡券失败: {e}")
                return None

    def update_card(self, card_id: int, name: str = None, card_type: str = None,
                   api_config: dict = None, text_content: str = None, data_content: str = None,
                   image_url: str = None, description: str = None, enabled: bool = None,
                   delay_seconds: int = None, is_multi_spec: bool = None,
                   spec_name: str = None, spec_value: str = None) -> bool:
        """更新卡券"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                # 构建动态更新语句
                update_fields = []
                params = []
                
                if name is not None:
                    update_fields.append("name = ?")
                    params.append(name)
                if card_type is not None:
                    update_fields.append("type = ?")
                    params.append(card_type)
                if api_config is not None:
                    update_fields.append("api_config = ?")
                    params.append(json.dumps(api_config, ensure_ascii=False))
                if text_content is not None:
                    update_fields.append("text_content = ?")
                    params.append(text_content)
                if data_content is not None:
                    update_fields.append("data_content = ?")
                    params.append(data_content)
                if image_url is not None:
                    update_fields.append("image_url = ?")
                    params.append(image_url)
                if description is not None:
                    update_fields.append("description = ?")
                    params.append(description)
                if enabled is not None:
                    update_fields.append("enabled = ?")
                    params.append(enabled)
                if delay_seconds is not None:
                    update_fields.append("delay_seconds = ?")
                    params.append(delay_seconds)
                if is_multi_spec is not None:
                    update_fields.append("is_multi_spec = ?")
                    params.append(is_multi_spec)
                if spec_name is not None:
                    update_fields.append("spec_name = ?")
                    params.append(spec_name)
                if spec_value is not None:
                    update_fields.append("spec_value = ?")
                    params.append(spec_value)
                
                if not update_fields:
                    return True
                
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                params.append(card_id)
                
                sql = f"UPDATE cards SET {', '.join(update_fields)} WHERE id = ?"
                self._execute_sql(cursor, sql, params)
                
                success = cursor.rowcount > 0
                self.conn.commit()
                return success
            except Exception as e:
                logger.error(f"更新卡券失败: {e}")
                if self.conn:
                    self.conn.rollback()
                return False

    def delete_card(self, card_id: int) -> bool:
        """删除卡券"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, 'DELETE FROM cards WHERE id = ?', (card_id,))
                
                success = cursor.rowcount > 0
                self.conn.commit()
                return success
            except Exception as e:
                logger.error(f"删除卡券失败: {e}")
                if self.conn:
                    self.conn.rollback()
                return False

    # ==================== 自动发货规则管理方法 ====================
    
    def get_all_delivery_rules(self, user_id: int) -> list:
        """获取用户的所有发货规则"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    SELECT dr.id, dr.keyword, dr.card_id, dr.delivery_count, dr.enabled,
                           dr.description, dr.created_at, dr.updated_at, c.name as card_name
                    FROM delivery_rules dr
                    LEFT JOIN cards c ON dr.card_id = c.id
                    WHERE dr.user_id = ?
                    ORDER BY dr.created_at DESC
                ''', (user_id,))
                
                rules = []
                for row in cursor.fetchall():
                    rules.append({
                        'id': row[0],
                        'keyword': row[1],
                        'card_id': row[2],
                        'delivery_count': row[3],
                        'enabled': bool(row[4]),
                        'description': row[5],
                        'created_at': row[6],
                        'updated_at': row[7],
                        'card_name': row[8]
                    })
                
                return rules
            except Exception as e:
                logger.error(f"获取发货规则列表失败: {e}")
                return []

    def create_delivery_rule(self, keyword: str, card_id: int, delivery_count: int = 1,
                           enabled: bool = True, description: str = '', user_id: int = 1) -> int:
        """创建发货规则"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    INSERT INTO delivery_rules (keyword, card_id, delivery_count, enabled,
                                              description, user_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (keyword, card_id, delivery_count, enabled, description, user_id))
                
                rule_id = cursor.lastrowid
                self.conn.commit()
                logger.info(f"发货规则创建成功: {keyword} (ID: {rule_id})")
                return rule_id
            except Exception as e:
                logger.error(f"创建发货规则失败: {e}")
                if self.conn:
                    self.conn.rollback()
                raise

    def get_delivery_rule_by_id(self, rule_id: int, user_id: int) -> dict:
        """根据ID获取发货规则"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    SELECT dr.id, dr.keyword, dr.card_id, dr.delivery_count, dr.enabled,
                           dr.description, dr.created_at, dr.updated_at, c.name as card_name
                    FROM delivery_rules dr
                    LEFT JOIN cards c ON dr.card_id = c.id
                    WHERE dr.id = ? AND dr.user_id = ?
                ''', (rule_id, user_id))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'keyword': row[1],
                        'card_id': row[2],
                        'delivery_count': row[3],
                        'enabled': bool(row[4]),
                        'description': row[5],
                        'created_at': row[6],
                        'updated_at': row[7],
                        'card_name': row[8]
                    }
                return None
            except Exception as e:
                logger.error(f"获取发货规则失败: {e}")
                return None

    def update_delivery_rule(self, rule_id: int, keyword: str = None, card_id: int = None,
                           delivery_count: int = None, enabled: bool = None,
                           description: str = None, user_id: int = None) -> bool:
        """更新发货规则"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                # 构建动态更新语句
                update_fields = []
                params = []
                
                if keyword is not None:
                    update_fields.append("keyword = ?")
                    params.append(keyword)
                if card_id is not None:
                    update_fields.append("card_id = ?")
                    params.append(card_id)
                if delivery_count is not None:
                    update_fields.append("delivery_count = ?")
                    params.append(delivery_count)
                if enabled is not None:
                    update_fields.append("enabled = ?")
                    params.append(enabled)
                if description is not None:
                    update_fields.append("description = ?")
                    params.append(description)
                
                if not update_fields:
                    return True
                
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                
                # 添加WHERE条件参数
                params.append(rule_id)
                if user_id is not None:
                    where_clause = "WHERE id = ? AND user_id = ?"
                    params.append(user_id)
                else:
                    where_clause = "WHERE id = ?"
                
                sql = f"UPDATE delivery_rules SET {', '.join(update_fields)} {where_clause}"
                self._execute_sql(cursor, sql, params)
                
                success = cursor.rowcount > 0
                self.conn.commit()
                return success
            except Exception as e:
                logger.error(f"更新发货规则失败: {e}")
                if self.conn:
                    self.conn.rollback()
                return False

    def delete_delivery_rule(self, rule_id: int, user_id: int = None) -> bool:
        """删除发货规则"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                if user_id is not None:
                    self._execute_sql(cursor, 'DELETE FROM delivery_rules WHERE id = ? AND user_id = ?', 
                                    (rule_id, user_id))
                else:
                    self._execute_sql(cursor, 'DELETE FROM delivery_rules WHERE id = ?', (rule_id,))
                
                success = cursor.rowcount > 0
                self.conn.commit()
                return success
            except Exception as e:
                logger.error(f"删除发货规则失败: {e}")
                if self.conn:
                    self.conn.rollback()
                return False

    # ==================== 消息通知管理方法 ====================
    
    def get_all_message_notifications(self) -> dict:
        """获取所有消息通知配置"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    SELECT cookie_id, channel_id, enabled, created_at, updated_at
                    FROM message_notifications
                    ORDER BY created_at DESC
                ''')
                
                notifications = {}
                for row in cursor.fetchall():
                    cookie_id = row[0]
                    if cookie_id not in notifications:
                        notifications[cookie_id] = []
                    
                    notifications[cookie_id].append({
                        'channel_id': row[1],
                        'enabled': bool(row[2]),
                        'created_at': row[3],
                        'updated_at': row[4]
                    })
                
                return notifications
            except Exception as e:
                logger.error(f"获取所有消息通知配置失败: {e}")
                return {}

    def get_account_notifications(self, cookie_id: str) -> list:
        """获取指定账号的消息通知配置"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                # 检查表结构，确保兼容性
                try:
                    cursor.execute("PRAGMA table_info(message_notifications)")
                    columns = cursor.fetchall()
                    column_names = [col[1] for col in columns]
                    
                    # 检查是否有channel_id列
                    if 'channel_id' in column_names:
                        self._execute_sql(cursor, '''
                            SELECT mn.id, mn.channel_id, mn.enabled, mn.created_at, mn.updated_at,
                                   nc.name as channel_name, nc.type as channel_type
                            FROM message_notifications mn
                            LEFT JOIN notification_channels nc ON mn.channel_id = nc.id
                            WHERE mn.cookie_id = ?
                            ORDER BY mn.created_at DESC
                        ''', (cookie_id,))
                    else:
                        # 旧版本表结构，返回空结果避免错误
                        logger.warning(f"message_notifications表缺少channel_id列，跳过查询")
                        return []
                except Exception as table_error:
                    logger.warning(f"检查表结构失败，跳过查询: {table_error}")
                    return []
                
                notifications = []
                for row in cursor.fetchall():
                    notifications.append({
                        'id': row[0],
                        'channel_id': row[1],
                        'enabled': bool(row[2]),
                        'created_at': row[3],
                        'updated_at': row[4],
                        'channel_name': row[5],
                        'channel_type': row[6]
                    })
                
                return notifications
            except Exception as e:
                logger.error(f"获取账号消息通知配置失败: {e}")
                return []

    def set_message_notification(self, cookie_id: str, channel_id: int, enabled: bool) -> bool:
        """设置消息通知"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, '''
                    INSERT OR REPLACE INTO message_notifications 
                    (cookie_id, channel_id, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (cookie_id, channel_id, enabled))
                
                self.conn.commit()
                return True
            except Exception as e:
                logger.error(f"设置消息通知失败: {e}")
                if self.conn:
                    self.conn.rollback()
                return False

    def delete_account_notifications(self, cookie_id: str) -> bool:
        """删除账号的所有消息通知配置"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, 'DELETE FROM message_notifications WHERE cookie_id = ?', (cookie_id,))
                
                success = cursor.rowcount > 0
                self.conn.commit()
                return success
            except Exception as e:
                logger.error(f"删除账号消息通知配置失败: {e}")
                if self.conn:
                    self.conn.rollback()
                return False

    def delete_message_notification(self, notification_id: int) -> bool:
        """删除消息通知配置"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, 'DELETE FROM message_notifications WHERE id = ?', (notification_id,))
                
                success = cursor.rowcount > 0
                self.conn.commit()
                return success
            except Exception as e:
                logger.error(f"删除消息通知配置失败: {e}")
                if self.conn:
                    self.conn.rollback()
                return False

    def get_all_system_settings(self) -> dict:
        """获取所有系统设置"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                self._execute_sql(cursor, 'SELECT key, value, description FROM system_settings')
                
                settings = {}
                for row in cursor.fetchall():
                    settings[row[0]] = {
                        'value': row[1],
                        'description': row[2]
                    }
                
                return settings
            except Exception as e:
                logger.error(f"获取所有系统设置失败: {e}")
                return {}

    def get_table_data(self, table_name: str) -> tuple:
        """获取指定表的所有数据和列名（管理员专用）"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                # 获取表的列信息
                self._execute_sql(cursor, f"PRAGMA table_info({table_name})")
                columns_info = cursor.fetchall()
                columns = [col[1] for col in columns_info]  # col[1] 是列名
                
                # 获取表数据
                self._execute_sql(cursor, f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                
                # 将数据转换为字典列表
                data = []
                for row in rows:
                    row_dict = {}
                    for i, value in enumerate(row):
                        if i < len(columns):
                            row_dict[columns[i]] = value
                    data.append(row_dict)
                
                logger.info(f"获取表 {table_name} 数据成功，共 {len(data)} 条记录")
                return data, columns
                
            except Exception as e:
                logger.error(f"获取表 {table_name} 数据失败: {e}")
                return [], []

    def get_keywords(self, cookie_id: str):
        """获取关键词列表"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                # 从keywords表获取关键词数据
                cursor.execute('''
                    SELECT keyword 
                    FROM keywords 
                    WHERE cookie_id = ?
                    ORDER BY keyword
                ''', (cookie_id,))
                
                results = cursor.fetchall()
                return [row[0] for row in results] if results else []
                
            except sqlite3.Error as e:
                logger.error(f"获取关键词失败: {e}")
                return []

    def get_keywords_with_item_id(self, cookie_id: str):
        """获取包含商品ID的关键词列表"""
        with self.lock:
            try:
                if not self.conn:
                    self.init_db()
                cursor = self.conn.cursor()
                
                # 从keywords表获取关键词数据
                cursor.execute('''
                    SELECT keyword, reply, item_id 
                    FROM keywords 
                    WHERE cookie_id = ?
                    ORDER BY keyword
                ''', (cookie_id,))
                
                results = cursor.fetchall()
                return results if results else []
                
            except sqlite3.Error as e:
                logger.error(f"获取关键词失败: {e}")
                return []

# 创建全局数据库管理器实例
db_manager = DatabaseManager()