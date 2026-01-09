import json
import logging
import os
import sqlite3
from sqlite3 import Error as SQLiteError

import mysql.connector
from mysql.connector import Error as MySQLError
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Database:
    """Database abstraction preferring MySQL with an automatic SQLite fallback."""

    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.user = os.getenv("DB_USER", "root")
        self.password = os.getenv("DB_PASSWORD", "")
        self.database = os.getenv("DB_NAME", "live_assistant")

        self.backend = "mysql"
        self.pool = None
        self.mysql_error = None

        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)
        self.sqlite_path = os.path.join(data_dir, "local_db.sqlite3")

        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name="mypool",
                pool_size=5,
                pool_reset_session=True,
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                ssl_disabled=True,
            )
            logger.info("✅ 数据库连接池创建成功 (MySQL)")
        except MySQLError as err:
            self.pool = None
            self.backend = "sqlite"
            self.mysql_error = err
            logger.error(f"❌ 数据库连接池创建失败，已回退到 SQLite: {err}")
            self._ensure_sqlite_db()

        self.blacklist_file = os.path.join(os.path.dirname(__file__), "data", "blacklist.json")
        self.whitelist_file = os.path.join(os.path.dirname(__file__), "data", "whitelist.json")

        self.init_tables()

    def _ensure_sqlite_db(self):
        """Ensure the SQLite database file exists before first use."""
        if os.path.exists(self.sqlite_path):
            logger.info(f"ℹ️ 使用本地 SQLite 数据库: {self.sqlite_path}")
            return

        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.close()
            logger.info(f"✅ 已创建本地 SQLite 数据库: {self.sqlite_path}")
        except SQLiteError as err:
            logger.error(f"❌ 无法创建本地 SQLite 数据库: {err}")

    def _load_json_file(self, path):
        try:
            if not os.path.exists(path):
                return {}
            with open(path, 'r', encoding='utf-8') as handle:
                return json.load(handle)
        except Exception as err:
            logger.warning(f"无法加载 JSON 文件 {path}: {err}")
            return {}

    def _fallback_to_sqlite(self, reason):
        """Downgrade to SQLite backend after persistent MySQL failures."""
        if self.backend == "sqlite":
            return

        self.backend = "sqlite"
        self.pool = None
        self.mysql_error = reason
        logger.warning(f"⚠️ MySQL 连接不可用，回退到 SQLite：{reason}")
        self._ensure_sqlite_db()
        # 初始化 SQLite 表结构，确保后续查询可用
        self._init_tables_sqlite()

    def get_connection(self):
        """Return a database connection for the active backend."""
        if self.backend == "mysql":
            try:
                if self.pool:
                    return self.pool.get_connection()
                return mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    ssl_disabled=True,
                )
            except MySQLError as err:
                logger.error(f"❌ 获取数据库连接失败: {err}")
                self._fallback_to_sqlite(err)
                return self.get_connection()

        try:
            conn = sqlite3.connect(self.sqlite_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        except SQLiteError as err:
            logger.error(f"❌ 获取数据库连接失败: {err}")
            return None

    def _get_cursor(self, conn, dictionary=False):
        if self.backend == "mysql":
            return conn.cursor(dictionary=dictionary)

        if dictionary:
            conn.row_factory = sqlite3.Row
        return conn.cursor()

    def _now_func(self):
        return "NOW()" if self.backend == "mysql" else "CURRENT_TIMESTAMP"

    def _normalize_query(self, query):
        if self.backend != "sqlite":
            return query

        replacements = {
            "NOW()": "CURRENT_TIMESTAMP",
            "BOOLEAN": "INTEGER",
        }
        for source, target in replacements.items():
            query = query.replace(source, target)
        return query.replace("%s", "?")

    def _execute(self, cursor, query, params=None):
        if params is None:
            params = ()
        elif isinstance(params, list):
            params = tuple(params)

        cursor.execute(self._normalize_query(query), params)

    def _row_to_dict(self, row):
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        if hasattr(row, "keys"):
            return {key: row[key] for key in row.keys()}
        return row

    def _deep_merge_dicts(self, base, incoming):
        """深度合并 incoming 到 base（就地修改 base），遇到冲突时以 incoming 为准。
        仅在两者均为 dict 时递归合并；其他类型直接覆盖。
        返回合并后的 base。
        """
        if not isinstance(base, dict) or not isinstance(incoming, dict):
            return incoming
        for k, v in incoming.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_merge_dicts(base[k], v)
            else:
                base[k] = v
        return base

    def _rows_to_dicts(self, rows):
        if not rows:
            return []
        return [self._row_to_dict(row) for row in rows]

    def init_tables(self):
        if self.backend == "mysql":
            self._init_tables_mysql()
        else:
            if self.mysql_error:
                logger.warning(f"⚠️ 使用 SQLite 作为后端，MySQL 错误: {self.mysql_error}")
            self._init_tables_sqlite()

    def _init_tables_mysql(self):
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return

            cursor = self._get_cursor(conn)

            self._execute(
                cursor,
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id VARCHAR(36) PRIMARY KEY,
                    host_name VARCHAR(255) NOT NULL,
                    live_theme VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
                """,
            )

            self._execute(
                cursor,
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(36),
                    product_name VARCHAR(255) NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    unit VARCHAR(20) DEFAULT '元',
                    product_type VARCHAR(50),
                    attributes JSON,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """,
            )

            try:
                self._execute(
                    cursor,
                    "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = 'products' AND column_name = 'unit'",
                    (self.database,),
                )
                if cursor.fetchone()[0] == 0:
                    self._execute(cursor, "ALTER TABLE products ADD COLUMN unit VARCHAR(20) DEFAULT '元'")

                self._execute(
                    cursor,
                    "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = 'products' AND column_name = 'product_type'",
                    (self.database,),
                )
                if cursor.fetchone()[0] == 0:
                    self._execute(cursor, "ALTER TABLE products ADD COLUMN product_type VARCHAR(50)")

                self._execute(
                    cursor,
                    "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = 'products' AND column_name = 'attributes'",
                    (self.database,),
                )
                if cursor.fetchone()[0] == 0:
                    self._execute(cursor, "ALTER TABLE products ADD COLUMN attributes JSON")
            except Exception as err:
                logger.warning(f"⚠️ 无法确保 products 表字段完整: {err}")

            self._execute(
                cursor,
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(36),
                    user_message TEXT,
                    ai_response TEXT,
                    audio_url VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """,
            )

            self._execute(
                cursor,
                """
                CREATE TABLE IF NOT EXISTS bullet_screen_queue (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(36),
                    username VARCHAR(255),
                    message TEXT NOT NULL,
                    category VARCHAR(50) DEFAULT 'unknown',
                    priority INT DEFAULT 0,
                    is_processed BOOLEAN DEFAULT FALSE,
                    confidence_score FLOAT DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    INDEX idx_session_processed (session_id, is_processed),
                    INDEX idx_created (created_at)
                )
                """,
            )

            self._execute(
                cursor,
                """
                CREATE TABLE IF NOT EXISTS blacklist (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(36),
                    pattern VARCHAR(255) NOT NULL,
                    type VARCHAR(20) DEFAULT 'message',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    INDEX idx_session_type (session_id, type)
                )
                """,
            )

            self._execute(
                cursor,
                """
                CREATE TABLE IF NOT EXISTS whitelist (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(36),
                    pattern VARCHAR(255) NOT NULL,
                    answer TEXT NOT NULL,
                    priority INT DEFAULT 0,
                    product_types VARCHAR(255),
                    hit_count INT DEFAULT 0,
                    last_hit_at TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    INDEX idx_session_pattern (session_id),
                    INDEX idx_hit_count (hit_count)
                )
                """,
            )

            try:
                self._execute(
                    cursor,
                    "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = 'whitelist' AND column_name = 'priority'",
                    (self.database,),
                )
                if cursor.fetchone()[0] == 0:
                    self._execute(cursor, "ALTER TABLE whitelist ADD COLUMN priority INT DEFAULT 0 AFTER answer")
                    logger.info("✅ 已添加 whitelist.priority 字段")

                self._execute(
                    cursor,
                    "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = 'whitelist' AND column_name = 'product_types'",
                    (self.database,),
                )
                if cursor.fetchone()[0] == 0:
                    self._execute(cursor, "ALTER TABLE whitelist ADD COLUMN product_types VARCHAR(255) AFTER priority")
                    logger.info("✅ 已添加 whitelist.product_types 字段")

                self._execute(
                    cursor,
                    "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = 'whitelist' AND column_name = 'hit_count'",
                    (self.database,),
                )
                if cursor.fetchone()[0] == 0:
                    self._execute(cursor, "ALTER TABLE whitelist ADD COLUMN hit_count INT DEFAULT 0 AFTER product_types")
                    logger.info("✅ 已添加 whitelist.hit_count 字段")

                self._execute(
                    cursor,
                    "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = 'whitelist' AND column_name = 'last_hit_at'",
                    (self.database,),
                )
                if cursor.fetchone()[0] == 0:
                    self._execute(cursor, "ALTER TABLE whitelist ADD COLUMN last_hit_at TIMESTAMP NULL AFTER hit_count")
                    logger.info("✅ 已添加 whitelist.last_hit_at 字段")
            except Exception as err:
                logger.warning(f"⚠️ 无法添加 whitelist 字段: {err}")

            # 确保 conversations 和 qa_cache 表包含 audio_url 字段（兼容已有表）
            try:
                self._execute(
                    cursor,
                    "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = 'conversations' AND column_name = 'audio_url'",
                    (self.database,),
                )
                if cursor.fetchone()[0] == 0:
                    self._execute(cursor, "ALTER TABLE conversations ADD COLUMN audio_url VARCHAR(255) NULL AFTER ai_response")
                    logger.info("✅ 已添加 conversations.audio_url 字段")

                self._execute(
                    cursor,
                    "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = 'qa_cache' AND column_name = 'audio_url'",
                    (self.database,),
                )
                if cursor.fetchone()[0] == 0:
                    self._execute(cursor, "ALTER TABLE qa_cache ADD COLUMN audio_url VARCHAR(255) NULL AFTER answer")
                    logger.info("✅ 已添加 qa_cache.audio_url 字段")
            except Exception as err:
                logger.warning(f"⚠️ 无法确保 audio_url 字段存在: {err}")

            self._execute(
                cursor,
                """
                CREATE TABLE IF NOT EXISTS faq_templates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    product_type VARCHAR(50) NOT NULL,
                    pattern VARCHAR(255) NOT NULL,
                    answer_template VARCHAR(500) NOT NULL,
                    placeholder VARCHAR(100),
                    priority INT DEFAULT 80,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_product_type (product_type)
                )
                """,
            )

            self._execute(
                cursor,
                """
                CREATE TABLE IF NOT EXISTS qa_cache (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(36),
                    question TEXT NOT NULL,
                    question_hash VARCHAR(64) NOT NULL,
                    answer TEXT NOT NULL,
                    audio_url VARCHAR(255),
                    hit_count INT DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    INDEX idx_session_hash (session_id, question_hash),
                    INDEX idx_last_used (last_used_at)
                )
                """,
            )

            # 产品信息表：用于存储每个会话/商品的补充信息（如产地、产区、保养建议等）
            self._execute(
                cursor,
                """
                CREATE TABLE IF NOT EXISTS product_info (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(36),
                    product_id INT,
                    product_name VARCHAR(255),
                    info_key VARCHAR(100),
                    info_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    INDEX idx_session_product (session_id, product_name)
                )
                """,
            )

            conn.commit()

            self._execute(cursor, "SELECT COUNT(*) FROM faq_templates")
            if cursor.fetchone()[0] == 0:
                self._init_faq_templates(cursor)
                conn.commit()

            logger.info("✅ 数据库表初始化成功 (MySQL)")
        except Exception as err:
            logger.error(f"❌ 数据库表初始化失败 (MySQL): {err}")
        finally:
            if conn:
                conn.close()

    def _sqlite_table_has_column(self, cursor, table, column):
        cursor.execute(f"PRAGMA table_info({table})")
        rows = cursor.fetchall()
        names = {row[1] if isinstance(row, tuple) else row[1] for row in rows}
        return column in names

    def _init_tables_sqlite(self):
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return

            cursor = self._get_cursor(conn)

            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    host_name TEXT NOT NULL,
                    live_theme TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    product_name TEXT NOT NULL,
                    price REAL NOT NULL,
                    unit TEXT DEFAULT '元',
                    product_type TEXT,
                    attributes TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )

            if not self._sqlite_table_has_column(cursor, "products", "unit"):
                cursor.execute("ALTER TABLE products ADD COLUMN unit TEXT DEFAULT '元'")
            if not self._sqlite_table_has_column(cursor, "products", "product_type"):
                cursor.execute("ALTER TABLE products ADD COLUMN product_type TEXT")
            if not self._sqlite_table_has_column(cursor, "products", "attributes"):
                cursor.execute("ALTER TABLE products ADD COLUMN attributes TEXT")

            # 确保 conversations 表包含 audio_url 字段
            if not self._sqlite_table_has_column(cursor, "conversations", "audio_url"):
                try:
                    cursor.execute("ALTER TABLE conversations ADD COLUMN audio_url TEXT")
                    logger.info("✅ 已为 SQLite conversations 添加 audio_url 字段")
                except Exception:
                    pass

            # 确保 qa_cache 表包含 audio_url 字段
            if not self._sqlite_table_has_column(cursor, "qa_cache", "audio_url"):
                try:
                    cursor.execute("ALTER TABLE qa_cache ADD COLUMN audio_url TEXT")
                    logger.info("✅ 已为 SQLite qa_cache 添加 audio_url 字段")
                except Exception:
                    pass

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    user_message TEXT,
                    ai_response TEXT,
                    audio_url TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS bullet_screen_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    username TEXT,
                    message TEXT NOT NULL,
                    category TEXT DEFAULT 'unknown',
                    priority INTEGER DEFAULT 0,
                    is_processed INTEGER DEFAULT 0,
                    confidence_score REAL DEFAULT 0.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed_at DATETIME,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_session_processed ON bullet_screen_queue (session_id, is_processed)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_created ON bullet_screen_queue (created_at)"
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    pattern TEXT NOT NULL,
                    type TEXT DEFAULT 'message',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_session_type ON blacklist (session_id, type)"
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS whitelist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    pattern TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    product_types TEXT,
                    hit_count INTEGER DEFAULT 0,
                    last_hit_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_session_pattern ON whitelist (session_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_hit_count ON whitelist (hit_count)"
            )

            if not self._sqlite_table_has_column(cursor, "whitelist", "priority"):
                cursor.execute("ALTER TABLE whitelist ADD COLUMN priority INTEGER DEFAULT 0")
            if not self._sqlite_table_has_column(cursor, "whitelist", "product_types"):
                cursor.execute("ALTER TABLE whitelist ADD COLUMN product_types TEXT")
            if not self._sqlite_table_has_column(cursor, "whitelist", "hit_count"):
                cursor.execute("ALTER TABLE whitelist ADD COLUMN hit_count INTEGER DEFAULT 0")
            if not self._sqlite_table_has_column(cursor, "whitelist", "last_hit_at"):
                cursor.execute("ALTER TABLE whitelist ADD COLUMN last_hit_at DATETIME")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS faq_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_type TEXT NOT NULL,
                    pattern TEXT NOT NULL,
                    answer_template TEXT NOT NULL,
                    placeholder TEXT,
                    priority INTEGER DEFAULT 80,
                    is_active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_product_type ON faq_templates (product_type)"
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS qa_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    question TEXT NOT NULL,
                    question_hash TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    audio_url TEXT,
                    hit_count INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )

            # SQLite: product_info 表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS product_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    product_id INTEGER,
                    product_name TEXT,
                    info_key TEXT,
                    info_value TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_session_hash ON qa_cache (session_id, question_hash)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_last_used ON qa_cache (last_used_at)"
            )

            conn.commit()

            self._execute(cursor, "SELECT COUNT(*) FROM faq_templates")
            if cursor.fetchone()[0] == 0:
                self._init_faq_templates(cursor)
                conn.commit()

            logger.info("✅ 数据库表初始化成功 (SQLite)")
        except Exception as err:
            logger.error(f"❌ 数据库表初始化失败 (SQLite): {err}")
        finally:
            if conn:
                conn.close()

    def _init_faq_templates(self, cursor):
        templates = [
            ('fruit', '甜不甜', '我们的{name}甜度是{sweetness}，口感很好哦~', '甜度（如：9分甜）', 90),
            ('fruit', '甜度', '{name}的甜度是{sweetness}，非常适合喜欢吃甜的朋友！', '甜度（如：9分甜）', 90),
            ('fruit', '口感', '{name}的口感{texture}，吃起来特别满足！', '口感（如：多汁软糯）', 85),
            ('fruit', '产地', '我们的{name}来自{origin}，品质有保证！', '产地（如：云南）', 80),
            ('fruit', '哪里的', '{name}来自{origin}，品质有保证！', '产地（如：云南）', 80),
            ('fruit', '什么时候最好', '{name}在{season}最好吃，现在正是时候！', '季节（如：春季）', 75),
            ('vegetable', '新鲜吗', '绝对新鲜！{freshness}，当天采摘！', '新鲜度（如：当天现摘）', 90),
            ('vegetable', '怎么做', '这个{name}适合{cooking}，简单又好吃！', '烹饪方法（如：清炒或做汤）', 85),
            ('vegetable', '怎么吃', '推荐{cooking}，营养美味！', '烹饪方法（如：清炒或做汤）', 85),
            ('vegetable', '哪里的', '{name}来自{origin}，生态种植！', '产地（如：本地农场）', 80),
            ('vegetable', '产地', '来自{origin}，生态种植！', '产地（如：本地农场）', 80),
            ('meat', '怎么养的', '我们的{name}是{raising}，肉质鲜美！', '养殖方式（如：山地散养）', 90),
            ('meat', '养殖方式', '{raising}，保证品质！', '养殖方式（如：山地散养）', 90),
            ('meat', '肉质', '{name}的肉质{texture}，口感一流！', '肉质（如：紧实弹牙）', 85),
            ('meat', '口感', '肉质{texture}，口感一流！', '肉质（如：紧实弹牙）', 85),
            ('meat', '怎么煮', '建议{cooking_time}，味道最佳！', '烹饪时间（如：炖煮2小时）', 80),
            ('grain', '什么品种', '这是{variety}，品质优良！', '品种（如：东北大米）', 85),
            ('grain', '怎么吃', '{cooking}，营养健康！', '食用方法（如：煮粥或蒸饭）', 85),
            ('grain', '怎么做', '建议{cooking}，营养健康！', '食用方法（如：煮粥或蒸饭）', 85),
            ('grain', '哪里产的', '来自{origin}，原产地直供！', '产地（如：东北）', 80),
            ('grain', '产地', '{origin}，原产地直供！', '产地（如：东北）', 80),
            ('handicraft', '什么材料', '使用{material}材质，天然环保！', '材料（如：纯棉）', 85),
            ('handicraft', '怎么做的', '采用{craft}工艺，纯手工制作！', '工艺（如：传统编织）', 85),
            ('handicraft', '做多久', '每件需要{making_time}，匠心之作！', '制作时间（如：3天）', 80),
            ('processed', '什么原料', '原料是{ingredients}，健康放心！', '原料（如：纯天然水果）', 85),
            ('processed', '保质期', '保质期{shelf_life}，请放心购买！', '保质期（如：12个月）', 90),
            ('processed', '什么味道', '{flavor}风味，好吃不腻！', '风味（如：香甜可口）', 85),
        ]

        for product_type, pattern, answer_template, placeholder, priority in templates:
            self._execute(
                cursor,
                "INSERT INTO faq_templates (product_type, pattern, answer_template, placeholder, priority) VALUES (%s, %s, %s, %s, %s)",
                (product_type, pattern, answer_template, placeholder, priority),
            )

        logger.info(f"✅ 已初始化 {len(templates)} 条 FAQ 模板")

    # Remaining business methods stay identical to the original implementation but routed through helpers.
    # To keep the file concise, the implementations are lifted verbatim with `_execute` wrappers.

    def create_session(self, session_id, host_name, live_theme, products):
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return False

            cursor = self._get_cursor(conn)

            self._execute(
                cursor,
                "INSERT INTO sessions (id, host_name, live_theme) VALUES (%s, %s, %s)",
                (session_id, host_name, live_theme),
            )

            for product in products:
                ptype = product.get('product_type') or product.get('type')

                # 兼容：如果前端把产地/属性放在顶层字段（origin / 产地 / place_of_origin），
                # 则将其合并到 attributes 中再存储。
                raw_attrs = product.get('attributes', {})
                try:
                    if isinstance(raw_attrs, str) and raw_attrs:
                        attrs = json.loads(raw_attrs)
                    elif isinstance(raw_attrs, dict):
                        attrs = dict(raw_attrs)
                    else:
                        attrs = {}
                except Exception:
                    attrs = {}

                for alt in ('origin', '产地', 'place_of_origin', 'origin_place', 'product_origin'):
                    if alt in product and product.get(alt):
                        attrs.setdefault('origin', product.get(alt))

                attributes_json = json.dumps(attrs, ensure_ascii=False)

                self._execute(
                    cursor,
                    "INSERT INTO products (session_id, product_name, price, unit, product_type, attributes) VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        session_id,
                        product.get('name', ''),
                        float(product.get('price', 0)),
                        product.get('unit', '元'),
                        ptype,
                        attributes_json,
                    ),
                )

            conn.commit()
            logger.info(f"会话创建成功 - ID: {session_id}, 商品数量: {len(products)}")
            return True
        except Exception as err:
            logger.error(f"❌ 创建会话失败: {err}")
            return False
        finally:
            if conn:
                conn.close()

    def get_faq_templates(self, product_type):
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return []

            cursor = self._get_cursor(conn, dictionary=True)
            self._execute(
                cursor,
                "SELECT pattern, answer_template, placeholder, priority FROM faq_templates WHERE product_type = %s AND is_active = TRUE ORDER BY priority DESC",
                (product_type,),
            )
            return self._rows_to_dicts(cursor.fetchall())
        except Exception as err:
            logger.error(f"❌ 获取FAQ模板失败: {err}")
            return []
        finally:
            if conn:
                conn.close()

    def apply_faq_template(self, session_id, product_type, faq_values):
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return 0

            cursor = self._get_cursor(conn, dictionary=True)

            self._execute(
                cursor,
                "SELECT pattern, answer_template, priority FROM faq_templates WHERE product_type = %s AND is_active = TRUE",
                (product_type,),
            )
            templates = cursor.fetchall()

            applied_count = 0
            skipped_count = 0

            for template in templates:
                try:
                    answer = template['answer_template'].format(**faq_values)

                    self._execute(
                        cursor,
                        "SELECT COUNT(*) as cnt FROM whitelist WHERE session_id = %s AND pattern = %s",
                        (session_id, template['pattern']),
                    )
                    if cursor.fetchone()['cnt'] > 0:
                        continue

                    self._execute(
                        cursor,
                        "INSERT INTO whitelist (session_id, pattern, answer, priority, product_types) VALUES (%s, %s, %s, %s, %s)",
                        (session_id, template['pattern'], answer, template['priority'], product_type),
                    )
                    applied_count += 1
                except KeyError as err:
                    skipped_count += 1
                    logger.debug(f"FAQ模板缺少参数 {err}，跳过: {template['pattern']}")
                    continue

            conn.commit()
            logger.info(f"✅ 为会话 {session_id} 应用了 {applied_count} 条FAQ，跳过 {skipped_count} 条（缺少参数）")
            return applied_count
        except Exception as err:
            logger.error(f"❌ 应用FAQ模板失败: {err}")
            return 0
        finally:
            if conn:
                conn.close()

    def _get_session_product_types(self, session_id):
        session = self.get_session(session_id)
        if not session or 'products' not in session:
            return set()

        product_types = set()
        for product in session['products']:
            product_type = product.get('product_type')
            if product_type:
                product_types.add(product_type)

        return product_types

    def _check_product_type_match(self, item_types, session_product_types):
        if not item_types:
            return True

        if not session_product_types:
            return True

        item_type_list = [entry.strip() for entry in item_types.split(',')]
        return any(item for item in item_type_list if item in session_product_types)

    def get_session(self, session_id):
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return None

            cursor = self._get_cursor(conn, dictionary=True)

            self._execute(cursor, "SELECT * FROM sessions WHERE id = %s", (session_id,))
            session = self._row_to_dict(cursor.fetchone())

            if session:
                self._execute(cursor, "SELECT * FROM products WHERE session_id = %s", (session_id,))
                products = self._rows_to_dicts(cursor.fetchall())
                # 确保 products 中的 attributes 字段为 dict（若为 JSON 字符串则解析）
                for p in products:
                    try:
                        attrs = p.get('attributes')
                        if isinstance(attrs, str) and attrs:
                            p['attributes'] = json.loads(attrs)
                        elif attrs is None:
                            p['attributes'] = {}
                    except Exception:
                        p['attributes'] = {}
                session['products'] = products

                self._execute(
                    cursor,
                    "SELECT * FROM conversations WHERE session_id = %s ORDER BY created_at",
                    (session_id,),
                )
                session['conversations'] = self._rows_to_dicts(cursor.fetchall())

            return session
        except Exception as err:
            logger.error(f"❌ 获取会话失败: {err}")
            return None
        finally:
            if conn:
                conn.close()

    def save_conversation(self, session_id, user_message, ai_response, audio_url=None):
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return False

            cursor = self._get_cursor(conn)
            self._execute(
                cursor,
                "INSERT INTO conversations (session_id, user_message, ai_response, audio_url) VALUES (%s, %s, %s, %s)",
                (session_id, user_message, ai_response, audio_url),
            )
            conn.commit()
            logger.debug(f"对话已保存 - 会话ID: {session_id}")
            return True
        except Exception as err:
            logger.error(f"❌ 保存对话失败: {err}")
            return False
        finally:
            if conn:
                conn.close()

    def save_product_info(self, session_id, product_name=None, product_id=None, info_key=None, info_value=None):
        """保存单个商品的补充信息：同时写入 product_info 表，并合并更新 products.attributes 字段（若能找到对应商品）。"""
        if not session_id or not info_key:
            return False

        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return False

            cursor = self._get_cursor(conn)

            # 尝试找到 product id 与 attributes
            product_row = None
            if product_id:
                self._execute(cursor, "SELECT id, attributes FROM products WHERE id = %s AND session_id = %s", (product_id, session_id))
                product_row = cursor.fetchone()
            elif product_name:
                self._execute(cursor, "SELECT id, attributes FROM products WHERE product_name = %s AND session_id = %s LIMIT 1", (product_name, session_id))
                product_row = cursor.fetchone()

            prod_id = None
            existing_attrs = {}

            if product_row:
                # product_row can be dict or tuple
                if isinstance(product_row, dict):
                    prod_id = product_row.get('id')
                    raw_attrs = product_row.get('attributes')
                else:
                    prod_id = product_row[0]
                    raw_attrs = product_row[1]

                try:
                    if isinstance(raw_attrs, str) and raw_attrs:
                        existing_attrs = json.loads(raw_attrs)
                    elif isinstance(raw_attrs, dict):
                        existing_attrs = dict(raw_attrs)
                except Exception:
                    existing_attrs = {}

            # 准备 info_value 的存储形式：如果是对象/列表则序列化为 JSON 字符串以保留结构
            store_value = info_value
            try:
                if isinstance(info_value, (dict, list)):
                    store_value = json.dumps(info_value, ensure_ascii=False)
                else:
                    # 如果前端以字符串发送但可能是 JSON，尝试解析再序列化以统一格式
                    if isinstance(info_value, str):
                        s = info_value.strip()
                        if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
                            try:
                                parsed = json.loads(s)
                                store_value = json.dumps(parsed, ensure_ascii=False)
                            except Exception:
                                store_value = info_value
            except Exception:
                store_value = info_value

            # 插入 product_info 表（info_value 以文本保存在表中，可能是 JSON 字符串）
            self._execute(
                cursor,
                "INSERT INTO product_info (session_id, product_id, product_name, info_key, info_value) VALUES (%s, %s, %s, %s, %s)",
                (session_id, prod_id, product_name, info_key, store_value),
            )

            # 合并到 products.attributes 并更新（若找到了对应商品id）
            if prod_id:
                try:
                    # 解析现有 attributes
                    existing = existing_attrs if isinstance(existing_attrs, dict) else {}

                    # 解析存入值（若为 JSON 字符串则转为对象）
                    parsed_value = None
                    try:
                        if isinstance(store_value, str):
                            s = store_value.strip()
                            if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
                                parsed_value = json.loads(store_value)
                            else:
                                parsed_value = store_value
                        else:
                            parsed_value = store_value
                    except Exception:
                        parsed_value = store_value

                    # 进行合并：若现有值与新值均为 dict，则深度合并；否则以新值覆盖
                    if info_key in existing and isinstance(existing[info_key], dict) and isinstance(parsed_value, dict):
                        self._deep_merge_dicts(existing[info_key], parsed_value)
                    else:
                        existing[info_key] = parsed_value

                    attrs_json = json.dumps(existing, ensure_ascii=False)
                    self._execute(cursor, "UPDATE products SET attributes = %s WHERE id = %s", (attrs_json, prod_id))
                except Exception:
                    logger.warning('更新 products.attributes 失败', exc_info=True)

            conn.commit()
            logger.info(f"✅ 保存商品信息 - 会话: {session_id}, product_id: {prod_id}, {info_key}={info_value}")
            return True
        except Exception as err:
            logger.error(f"❌ 保存商品信息失败: {err}")
            return False
        finally:
            if conn:
                conn.close()

    def get_product_info(self, session_id, product_name=None, product_id=None):
        """返回合并后的商品信息 dict（attributes 与 product_info 表中的键值合并）。"""
        if not session_id:
            return {}

        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return {}

            cursor = self._get_cursor(conn, dictionary=True)

            prod_id = product_id
            attrs = {}

            if not prod_id and product_name:
                self._execute(cursor, "SELECT id, attributes FROM products WHERE session_id = %s AND product_name = %s LIMIT 1", (session_id, product_name))
                row = cursor.fetchone()
                if row:
                    prod_id = row['id'] if 'id' in row else row[0]
                    raw_attrs = row['attributes'] if 'attributes' in row else row[1]
                    try:
                        if isinstance(raw_attrs, str) and raw_attrs:
                            attrs = json.loads(raw_attrs)
                        elif isinstance(raw_attrs, dict):
                            attrs = dict(raw_attrs)
                        else:
                            attrs = {}
                    except Exception:
                        attrs = {}

            # 从 product_info 表中读取补充信息并合并（支持 info_value 为 JSON 字符串）
            if prod_id:
                self._execute(cursor, "SELECT info_key, info_value FROM product_info WHERE session_id = %s AND product_id = %s", (session_id, prod_id))
                for r in cursor.fetchall():
                    k = r['info_key'] if isinstance(r, dict) else r[0]
                    raw_v = r['info_value'] if isinstance(r, dict) else r[1]
                    if not k:
                        continue
                    # 尝试解析 info_value 为 JSON
                    v = raw_v
                    try:
                        if isinstance(raw_v, str):
                            s = raw_v.strip()
                            if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
                                v = json.loads(raw_v)
                    except Exception:
                        v = raw_v

                    # 合并策略：如果 attrs 中已有且两者为 dict，则深度合并；否则以最新值覆盖/设置
                    if k in attrs and isinstance(attrs[k], dict) and isinstance(v, dict):
                        self._deep_merge_dicts(attrs[k], v)
                    else:
                        attrs[k] = v

            return attrs
        except Exception as err:
            logger.error(f"❌ 获取商品信息失败: {err}")
            return {}
        finally:
            if conn:
                conn.close()

    def add_bullet_screen(self, session_id, username, message, category='unknown', priority=0):
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return None

            cursor = self._get_cursor(conn)
            self._execute(
                cursor,
                "INSERT INTO bullet_screen_queue (session_id, username, message, category, priority) VALUES (%s, %s, %s, %s, %s)",
                (session_id, username, message, category, priority),
            )
            conn.commit()
            return cursor.lastrowid
        except Exception as err:
            logger.error(f"❌ 添加弹幕失败: {err}")
            return None
        finally:
            if conn:
                conn.close()

    def is_blacklisted(self, session_id, username, message):
        try:
            data = self._load_json_file(self.blacklist_file)
            session_list = data.get(session_id) or []
            for item in session_list:
                pattern = item.get('pattern')
                item_type = item.get('type', 'message')
                if item_type == 'username' and pattern == username:
                    return True
                if item_type == 'message' and pattern and pattern.lower() in (message or '').lower():
                    return True
        except Exception:
            logger.debug("黑名单文件读取异常，回退到数据库查询")

        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return False

            cursor = self._get_cursor(conn)
            self._execute(
                cursor,
                "SELECT COUNT(*) FROM blacklist WHERE session_id = %s AND type = 'username' AND pattern = %s",
                (session_id, username),
            )
            if cursor.fetchone()[0] > 0:
                return True

            self._execute(
                cursor,
                "SELECT pattern FROM blacklist WHERE session_id = %s AND type = 'message'",
                (session_id,),
            )
            for row in cursor.fetchall():
                pattern = row[0] if not isinstance(row, dict) else row['pattern']
                if pattern and pattern.lower() in (message or '').lower():
                    return True

            return False
        except Exception as err:
            logger.error(f"❌ 检查黑名单失败: {err}")
            return False
        finally:
            if conn:
                conn.close()

    def get_whitelist_answer(self, session_id, message):
        session_product_types = self._get_session_product_types(session_id)

        try:
            data = self._load_json_file(self.whitelist_file)
            session_list = data.get(session_id) or []
            best = None
            best_score = (-1, -1)
            for item in session_list:
                pattern = item.get('pattern')
                answer = item.get('answer')
                priority = item.get('priority', 0)
                item_types = item.get('product_types', '')

                if not pattern:
                    continue

                if not self._check_product_type_match(item_types, session_product_types):
                    continue

                if pattern.lower() in (message or '').lower():
                    score = (int(priority), len(pattern))
                    if score > best_score:
                        best = answer
                        best_score = score

            if best:
                return best
        except Exception:
            logger.debug("白名单文件读取异常，回退到数据库查询")

        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return None
            cursor = self._get_cursor(conn, dictionary=True)
            self._execute(
                cursor,
                "SELECT id, pattern, answer, priority, product_types FROM whitelist WHERE session_id = %s",
                (session_id,),
            )
            rows = cursor.fetchall()
            if not rows:
                return None

            best = None
            best_score = (-1, -1)
            best_id = None

            for row in rows:
                pattern = row['pattern']
                answer = row['answer']
                priority = row['priority']
                item_types = row['product_types']
                faq_id = row['id']

                if not pattern:
                    continue

                if not self._check_product_type_match(item_types, session_product_types):
                    continue

                if pattern.lower() in (message or '').lower():
                    score = (int(priority or 0), len(pattern))
                    if score > best_score:
                        best = answer
                        best_score = score
                        best_id = faq_id

            if best and best_id:
                try:
                    timestamp_func = self._now_func()
                    self._execute(
                        cursor,
                        f"UPDATE whitelist SET hit_count = hit_count + 1, last_hit_at = {timestamp_func} WHERE id = %s",
                        (best_id,),
                    )
                    conn.commit()
                    logger.debug(f"✅ FAQ命中统计已更新 - ID: {best_id}")
                except Exception as err:
                    logger.warning(f"更新FAQ命中统计失败: {err}")

            return best
        except Exception as err:
            logger.error(f"❌ 获取白名单答案失败: {err}")
            return None
        finally:
            if conn:
                conn.close()

    def get_pending_bullet_screens(self, session_id, limit=10):
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return []

            cursor = self._get_cursor(conn, dictionary=True)
            self._execute(
                cursor,
                "SELECT * FROM bullet_screen_queue WHERE session_id = %s AND is_processed = FALSE ORDER BY priority DESC, created_at ASC LIMIT %s",
                (session_id, limit),
            )
            return self._rows_to_dicts(cursor.fetchall())
        except Exception as err:
            logger.error(f"❌ 获取待处理弹幕失败: {err}")
            return []
        finally:
            if conn:
                conn.close()

    def mark_bullet_screens_processed(self, bullet_screen_ids):
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return False

            cursor = self._get_cursor(conn)
            placeholders = ','.join(['%s'] * len(bullet_screen_ids))
            timestamp_func = self._now_func()
            self._execute(
                cursor,
                f"UPDATE bullet_screen_queue SET is_processed = TRUE, processed_at = {timestamp_func} WHERE id IN ({placeholders})",
                tuple(bullet_screen_ids),
            )
            conn.commit()
            return True
        except Exception as err:
            logger.error(f"❌ 标记弹幕已处理失败: {err}")
            return False
        finally:
            if conn:
                conn.close()

    def get_cached_answer(self, session_id, question):
        return self.get_cached_answer_with_origin(session_id, question, None)

    def get_cached_answer_with_origin(self, session_id, question, product_origin=None):
        import hashlib
        import re

        def normalize_question(text):
            text = text.strip()
            text = re.sub(r'[？?！!。.，,、；;：:""\'\'""（）()【】\[\]]', '', text)
            text = re.sub(r'(吗|呢|啊|哦|嘛|呀|哇|哈)+', '', text)
            text = text.replace('么', '吗')
            return ' '.join(text.split()).lower()

        question_normalized = normalize_question(question)
        # 将 product_origin 纳入缓存键，避免不同产地复用同一缓存答案
        composite = question_normalized + (f"|origin:{product_origin}" if product_origin else "")
        question_hash = hashlib.sha256(composite.encode('utf-8')).hexdigest()

        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return None

            cursor = self._get_cursor(conn, dictionary=True)
            self._execute(
                cursor,
                "SELECT answer, audio_url, id FROM qa_cache WHERE session_id = %s AND question_hash = %s ORDER BY last_used_at DESC LIMIT 1",
                (session_id, question_hash),
            )
            result = cursor.fetchone()

            if result:
                timestamp_func = self._now_func()
                self._execute(
                    cursor,
                    f"UPDATE qa_cache SET hit_count = hit_count + 1, last_used_at = {timestamp_func} WHERE id = %s",
                    (result['id'],),
                )
                conn.commit()
                logger.info(f"✅ 问答缓存命中 - 会话: {session_id}, 问题: {question_normalized[:20]}...")
                # 返回包含 answer 与 audio_url，便于避免重复合成
                return {'answer': result['answer'], 'audio_url': result.get('audio_url')}

            return None
        except Exception as err:
            logger.error(f"❌ 获取缓存答案失败: {err}")
            return None
        finally:
            if conn:
                conn.close()

    def cache_qa(self, session_id, question, answer, audio_url=None):
        return self.cache_qa_with_origin(session_id, question, answer, audio_url, None)

    def cache_qa_with_origin(self, session_id, question, answer, audio_url=None, product_origin=None):
        import hashlib
        import re

        def normalize_question(text):
            text = text.strip()
            text = re.sub(r'[？?！!。.，,、；;：:""\'\'""（）()【】\[\]]', '', text)
            text = re.sub(r'(吗|呢|啊|哦|嘛|呀|哇|哈)+', '', text)
            text = text.replace('么', '吗')
            return ' '.join(text.split()).lower()

        question_normalized = normalize_question(question)
        composite = question_normalized + (f"|origin:{product_origin}" if product_origin else "")
        question_hash = hashlib.sha256(composite.encode('utf-8')).hexdigest()

        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return False

            cursor = self._get_cursor(conn)
            self._execute(
                cursor,
                "SELECT id FROM qa_cache WHERE session_id = %s AND question_hash = %s",
                (session_id, question_hash),
            )
            existing = cursor.fetchone()

            if existing:
                timestamp_func = self._now_func()
                # 更新 answer 与 audio_url（如果提供）并增加 hit_count
                if audio_url is not None:
                    self._execute(
                        cursor,
                        f"UPDATE qa_cache SET answer = %s, audio_url = %s, hit_count = hit_count + 1, last_used_at = {timestamp_func} WHERE id = %s",
                        (answer, audio_url, existing[0]),
                    )
                else:
                    self._execute(
                        cursor,
                        f"UPDATE qa_cache SET answer = %s, hit_count = hit_count + 1, last_used_at = {timestamp_func} WHERE id = %s",
                        (answer, existing[0]),
                    )
            else:
                self._execute(
                    cursor,
                    "INSERT INTO qa_cache (session_id, question, question_hash, answer, audio_url) VALUES (%s, %s, %s, %s, %s)",
                    (session_id, question, question_hash, answer, audio_url),
                )

            conn.commit()
            logger.info(f"✅ 问答缓存已保存 - 会话: {session_id}, 问题: {question_normalized[:20]}...")
            self._clean_qa_cache()
            return True
        except Exception as err:
            logger.error(f"❌ 缓存问答失败: {err}")
            return False
        finally:
            if conn:
                conn.close()

    def _clean_qa_cache(self, max_cache_size=1000):
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return

            cursor = self._get_cursor(conn)
            cursor.execute("SELECT COUNT(*) FROM qa_cache")
            count = cursor.fetchone()[0]

            if count > max_cache_size:
                self._execute(
                    cursor,
                    """
                    DELETE FROM qa_cache 
                    WHERE id NOT IN (
                        SELECT id FROM (
                            SELECT id FROM qa_cache 
                            ORDER BY last_used_at DESC 
                            LIMIT %s
                        ) AS tmp
                    )
                    """,
                    (max_cache_size,),
                )
                deleted = cursor.rowcount
                conn.commit()
                if deleted > 0:
                    logger.info(f"✅ 已清理 {deleted} 条旧的问答缓存，保留最近 {max_cache_size} 条")
        except Exception as err:
            logger.warning(f"清理问答缓存失败: {err}")
        finally:
            if conn:
                conn.close()

    def check_sensitive_words(self, message):
        if not message:
            return False, []

        try:
            data = self._load_json_file(self.blacklist_file)
            global_list = data.get('_global', [])

            if not global_list:
                return False, []

            msg_lower = message.lower().strip()
            matched_words = []

            for word in global_list:
                if not word:
                    continue
                if word.lower().strip() in msg_lower:
                    matched_words.append(word)

            if matched_words:
                logger.warning(f"⚠️ 敏感词命中: {matched_words} - 消息: {message}")
                return True, matched_words

            return False, []
        except Exception as err:
            logger.error(f"❌ 检查敏感词失败: {err}")
            return False, []

    def get_faq_statistics(self, session_id=None):
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return None

            cursor = self._get_cursor(conn, dictionary=True)

            if session_id:
                self._execute(
                    cursor,
                    """
                    SELECT 
                        COUNT(*) as total_faqs,
                        SUM(hit_count) as total_hits,
                        AVG(hit_count) as avg_hits,
                        MAX(hit_count) as max_hits,
                        COUNT(CASE WHEN hit_count > 0 THEN 1 END) as used_faqs,
                        COUNT(CASE WHEN hit_count = 0 THEN 1 END) as unused_faqs
                    FROM whitelist 
                    WHERE session_id = %s
                    """,
                    (session_id,),
                )
                stats = self._row_to_dict(cursor.fetchone())

                self._execute(
                    cursor,
                    """
                    SELECT pattern, answer, hit_count, last_hit_at, product_types
                    FROM whitelist 
                    WHERE session_id = %s AND hit_count > 0
                    ORDER BY hit_count DESC 
                    LIMIT 10
                    """,
                    (session_id,),
                )
                hot_faqs = self._rows_to_dicts(cursor.fetchall())

                self._execute(
                    cursor,
                    """
                    SELECT pattern, answer, product_types
                    FROM whitelist 
                    WHERE session_id = %s AND hit_count = 0
                    ORDER BY created_at DESC
                    LIMIT 10
                    """,
                    (session_id,),
                )
                unused_faqs = self._rows_to_dicts(cursor.fetchall())

                return {
                    'session_id': session_id,
                    'statistics': stats,
                    'hot_faqs': hot_faqs,
                    'unused_faqs': unused_faqs,
                }

            self._execute(
                cursor,
                """
                SELECT 
                    COUNT(*) as total_faqs,
                    SUM(hit_count) as total_hits,
                    AVG(hit_count) as avg_hits,
                    COUNT(DISTINCT session_id) as total_sessions
                FROM whitelist
                """,
            )
            stats = self._row_to_dict(cursor.fetchone())

            self._execute(
                cursor,
                """
                SELECT w.pattern, w.answer, w.hit_count, w.product_types, s.host_name, s.live_theme
                FROM whitelist w
                LEFT JOIN sessions s ON w.session_id = s.id
                WHERE w.hit_count > 0
                ORDER BY w.hit_count DESC 
                LIMIT 20
                """,
            )
            hot_faqs = self._rows_to_dicts(cursor.fetchall())

            return {
                'statistics': stats,
                'hot_faqs': hot_faqs,
            }
        except Exception as err:
            logger.error(f"❌ 获取FAQ统计失败: {err}")
            return None
        finally:
            if conn:
                conn.close()

    def get_faq_recommendations(self, session_id, min_hit_count=10):
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                return []

            cursor = self._get_cursor(conn, dictionary=True)

            if self.backend == 'mysql':
                query = """
                    SELECT 
                        q.question,
                        q.answer,
                        q.hit_count,
                        q.last_used_at
                    FROM qa_cache q
                    WHERE q.session_id = %s 
                      AND q.hit_count >= %s
                      AND NOT EXISTS (
                          SELECT 1 FROM whitelist w 
                          WHERE w.session_id = q.session_id 
                          AND LOWER(q.question) LIKE CONCAT('%%', LOWER(w.pattern), '%%')
                      )
                    ORDER BY q.hit_count DESC
                    LIMIT 20
                """
            else:
                query = """
                    SELECT 
                        q.question,
                        q.answer,
                        q.hit_count,
                        q.last_used_at
                    FROM qa_cache q
                    WHERE q.session_id = %s 
                      AND q.hit_count >= %s
                      AND NOT EXISTS (
                          SELECT 1 FROM whitelist w 
                          WHERE w.session_id = q.session_id 
                          AND LOWER(q.question) LIKE '%' || LOWER(w.pattern) || '%'
                      )
                    ORDER BY q.hit_count DESC
                    LIMIT 20
                """

            self._execute(cursor, query, (session_id, min_hit_count))
            recommendations = self._rows_to_dicts(cursor.fetchall())
            logger.info(f"✅ 找到 {len(recommendations)} 条FAQ推荐 - 会话: {session_id}")
            return recommendations
        except Exception as err:
            logger.error(f"❌ 获取FAQ推荐失败: {err}")
            return []
        finally:
            if conn:
                conn.close()


db = Database()
