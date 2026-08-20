# database.py
"""
数据库操作模块
支持 SQLite 和 PostgreSQL
"""

import json
import random
import sqlite3
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from config import MIN_REASON_LENGTH, DATABASE_URL, USE_POSTGRES

logger = logging.getLogger(__name__)

if USE_POSTGRES:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        logger.info("✅ PostgreSQL 驱动已加载")
    except ImportError:
        logger.error("❌ 缺少 psycopg2，请运行: pip install psycopg2-binary")
        USE_POSTGRES = False
else:
    from config import DATABASE_PATH
    logger.info(f"📝 使用 SQLite: {DATABASE_PATH}")


def get_connection():
    """获取数据库连接"""
    if USE_POSTGRES:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            logger.debug("✅ PostgreSQL 连接成功")
            return conn
        except Exception as e:
            logger.error(f"❌ PostgreSQL 连接失败: {e}")
            raise
    else:
        try:
            from config import DATABASE_PATH
            db_dir = os.path.dirname(DATABASE_PATH)
            
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"📁 创建数据库目录: {db_dir}")
            
            conn = sqlite3.connect(DATABASE_PATH)
            conn.row_factory = sqlite3.Row
            logger.debug("✅ SQLite 连接成功")
            return conn
        except Exception as e:
            logger.error(f"❌ SQLite 连接失败: {e}")
            raise


class DatabaseHelper:
    """数据库操作助手类，统一处理连接生命周期和错误处理"""

    @contextmanager
    def connect(self):
        """数据库连接上下文管理器，自动提交并在出错时回滚"""
        conn = None
        try:
            conn = get_connection()
            yield conn
        except Exception:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if conn is not None:
                conn.close()

    def q(self, pg_query: str, sqlite_query: str) -> str:
        """根据数据库类型返回对应查询语句"""
        return pg_query if USE_POSTGRES else sqlite_query

    def execute(self, pg_query: str, sqlite_query: str, params: tuple = ()) -> None:
        """执行写操作并提交"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(self.q(pg_query, sqlite_query), params)
            conn.commit()

    def query_one(self, pg_query: str, sqlite_query: str, params: tuple = ()) -> Optional[Any]:
        """执行查询并返回单行结果"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(self.q(pg_query, sqlite_query), params)
            return cursor.fetchone()

    def query_all(self, pg_query: str, sqlite_query: str, params: tuple = ()) -> list:
        """执行查询并返回所有结果"""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(self.q(pg_query, sqlite_query), params)
            return cursor.fetchall() or []

    def upsert(self, pg_query: str, pg_params: tuple,
               sqlite_query: str, sqlite_params: tuple) -> None:
        """执行 upsert 操作，支持 PostgreSQL 和 SQLite 使用不同的参数"""
        with self.connect() as conn:
            cursor = conn.cursor()
            if USE_POSTGRES:
                cursor.execute(pg_query, pg_params)
            else:
                cursor.execute(sqlite_query, sqlite_params)
            conn.commit()


_db = DatabaseHelper()


def _normalize_teacher_name(name: str) -> str:
    """规范化教师标识输入"""
    return (name or "").strip().lstrip("@")


def _dedupe_teacher_names(names: list[str]) -> list[str]:
    """按忽略大小写的方式去重并保留顺序"""
    result = []
    seen = set()
    for name in names:
        clean_name = _normalize_teacher_name(name)
        if not clean_name:
            continue
        key = clean_name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(clean_name)
    return result


def _build_in_clause_params(values: list[str]) -> tuple[str, tuple]:
    """为 IN 查询构建占位符和参数"""
    placeholders = ", ".join(["%s" if USE_POSTGRES else "?"] * len(values))
    return f"({placeholders})", tuple(values)


def _get_teacher_aliases_with_conn(conn, teacher: str) -> list[str]:
    """获取与该教师同一 Telegram ID 关联的所有用户名别名"""
    teacher = _normalize_teacher_name(teacher)
    if not teacher:
        return []

    cursor = conn.cursor()
    teacher_id = ""

    cursor.execute(
        _db.q(
            "SELECT teacher_id FROM teachers WHERE LOWER(name) = LOWER(%s)",
            "SELECT teacher_id FROM teachers WHERE LOWER(name) = LOWER(?)"
        ),
        (teacher,)
    )
    row = cursor.fetchone()
    if row and row[0]:
        teacher_id = str(row[0]).strip()
    elif teacher.isdigit():
        teacher_id = teacher

    aliases = [teacher]
    if teacher_id:
        cursor.execute(
            _db.q(
                "SELECT name FROM teachers WHERE teacher_id = %s ORDER BY name",
                "SELECT name FROM teachers WHERE teacher_id = ? ORDER BY name"
            ),
            (teacher_id,)
        )
        aliases.extend([r[0] for r in cursor.fetchall() if r[0]])

    return _dedupe_teacher_names(aliases)


def _get_teacher_aliases(teacher: str) -> list[str]:
    """获取教师相关的所有用户名别名"""
    try:
        with _db.connect() as conn:
            aliases = _get_teacher_aliases_with_conn(conn, teacher)
        return aliases or [_normalize_teacher_name(teacher)]
    except Exception as e:
        logger.error(f"获取教师别名失败: {e}")
        normalized = _normalize_teacher_name(teacher)
        return [normalized] if normalized else []


def _migrate_add_score_columns(conn) -> None:
    """迁移：为旧数据库的 recs 表添加三个评分字段（幂等操作）"""
    cursor = conn.cursor()
    score_cols = ["score_teaching", "score_grading", "score_difficulty"]
    for col in score_cols:
        try:
            if USE_POSTGRES:
                cursor.execute(
                    f"ALTER TABLE recs ADD COLUMN IF NOT EXISTS {col} INTEGER DEFAULT NULL"
                )
            else:
                # SQLite 不支持 IF NOT EXISTS，需捕获异常
                cursor.execute(f"ALTER TABLE recs ADD COLUMN {col} INTEGER DEFAULT NULL")
            conn.commit()
        except Exception:
            conn.rollback()


def init_db() -> None:
    """初始化数据库"""
    try:
        with _db.connect() as conn:
            cursor = conn.cursor()

            if USE_POSTGRES:
                logger.info("📊 初始化 PostgreSQL 表...")

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS recs (
                        id SERIAL PRIMARY KEY,
                        teacher TEXT NOT NULL,
                        user_id BIGINT NOT NULL,
                        recommend INTEGER NOT NULL,
                        reason TEXT NOT NULL,
                        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        score_teaching INTEGER DEFAULT NULL,
                        score_grading INTEGER DEFAULT NULL,
                        score_difficulty INTEGER DEFAULT NULL,
                        UNIQUE(teacher, user_id)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT DEFAULT '',
                        first_name TEXT DEFAULT '',
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS teachers (
                        name TEXT PRIMARY KEY,
                        nickname TEXT DEFAULT '',
                        teacher_id TEXT DEFAULT ''
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS blacklist (
                        user_id BIGINT PRIMARY KEY,
                        reason TEXT DEFAULT '',
                        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sub_admins (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT DEFAULT '',
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                try:
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teacher ON recs(teacher)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON recs(user_id)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_time ON recs(time)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teachers_teacher_id ON teachers(teacher_id)")
                except Exception:
                    conn.rollback()
            else:
                logger.info("📊 初始化 SQLite 表...")

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS recs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        teacher TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        recommend INTEGER NOT NULL,
                        reason TEXT NOT NULL,
                        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        score_teaching INTEGER DEFAULT NULL,
                        score_grading INTEGER DEFAULT NULL,
                        score_difficulty INTEGER DEFAULT NULL,
                        UNIQUE(teacher, user_id)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT DEFAULT '',
                        first_name TEXT DEFAULT '',
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS teachers (
                        name TEXT PRIMARY KEY,
                        nickname TEXT DEFAULT '',
                        teacher_id TEXT DEFAULT ''
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS blacklist (
                        user_id INTEGER PRIMARY KEY,
                        reason TEXT DEFAULT '',
                        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sub_admins (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT DEFAULT '',
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_teacher ON recs(teacher)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON recs(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_time ON recs(time)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_teachers_teacher_id ON teachers(teacher_id)")

            conn.commit()

            # 向后兼容：为旧数据库添加评分字段
            _migrate_add_score_columns(conn)

            db_info = "PostgreSQL" if USE_POSTGRES else "SQLite"
            logger.info(f"✅ {db_info} 数据库初始化成功")

    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


def check_user_rated_teacher(teacher: str, user_id: int) -> bool:
    """检查用户是否已评价该教师"""
    try:
        aliases = _get_teacher_aliases(teacher)
        if not aliases:
            return False

        in_clause, alias_params = _build_in_clause_params(aliases)
        with _db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT id FROM recs WHERE teacher IN {in_clause} AND user_id = "
                f"{'%s' if USE_POSTGRES else '?'} LIMIT 1",
                alias_params + (user_id,)
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"检查评价记录时出错: {e}")
        return False


def add_evaluation(teacher: str, recommend: int, reason: str, user_id: int,
                    score_teaching: Optional[int] = None,
                    score_grading: Optional[int] = None,
                    score_difficulty: Optional[int] = None) -> dict:
    """添加评价"""
    teacher = _normalize_teacher_name(teacher)
    if len(reason.strip()) < MIN_REASON_LENGTH:
        return {
            "success": False,
            "msg": f"❌ 理由太短！至少需要 {MIN_REASON_LENGTH} 个字\n\n您填写的: {len(reason)} 个字"
        }

    if check_user_rated_teacher(teacher, user_id):
        return {
            "success": False,
            "msg": f"❌ 您已经评价过 @{teacher} 了\n\n每个教师只能评价一次"
        }

    try:
        _db.execute(
            "INSERT INTO recs (teacher, user_id, recommend, reason, score_teaching, score_grading, score_difficulty)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)",
            "INSERT INTO recs (teacher, user_id, recommend, reason, score_teaching, score_grading, score_difficulty)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (teacher, user_id, recommend, reason, score_teaching, score_grading, score_difficulty)
        )
        logger.info(f"✅ 用户 {user_id} 成功评价了 {teacher}")
        return {"success": True, "msg": "✅ 评价提交成功！\n\n感谢您的反馈！"}
    except Exception as e:
        logger.error(f"添加评价失败: {e}")
        return {"success": False, "msg": f"❌ 提交失败: {str(e)}"}


def get_teacher_stats(teacher: str) -> dict:
    """获取教师的评价统计"""
    try:
        with _db.connect() as conn:
            cursor = conn.cursor()
            aliases = _get_teacher_aliases_with_conn(conn, teacher)
            if not aliases:
                return {"teacher": teacher, "total": 0, "recommend": 0, "not_recommend": 0, "latest": []}

            in_clause, alias_params = _build_in_clause_params(aliases)

            cursor.execute(f"SELECT COUNT(*) FROM recs WHERE teacher IN {in_clause}", alias_params)
            total = cursor.fetchone()[0]

            cursor.execute(
                f"SELECT COUNT(*) FROM recs WHERE teacher IN {in_clause} AND recommend = 1",
                alias_params
            )
            recommend_count = cursor.fetchone()[0]

            cursor.execute(
                f"SELECT COUNT(*) FROM recs WHERE teacher IN {in_clause} AND recommend = 0",
                alias_params
            )
            not_recommend_count = cursor.fetchone()[0]

            cursor.execute(
                f"SELECT id, user_id, recommend, reason, time FROM recs "
                f"WHERE teacher IN {in_clause} ORDER BY time DESC LIMIT 3",
                alias_params
            )
            latest = cursor.fetchall()

        return {
            "teacher": teacher,
            "total": total,
            "recommend": recommend_count,
            "not_recommend": not_recommend_count,
            "latest": latest
        }
    except Exception as e:
        logger.error(f"获取教师统计失败: {e}")
        return {"teacher": teacher, "total": 0, "recommend": 0, "not_recommend": 0, "latest": []}


def get_global_stats() -> dict:
    """获取全局统计"""
    try:
        with _db.connect() as conn:
            cursor = conn.cursor()
            q = _db.q

            cursor.execute("SELECT COUNT(*) FROM recs")
            total_eval = cursor.fetchone()[0]

            cursor.execute("SELECT DISTINCT teacher FROM recs")
            distinct_teachers = [row[0] for row in cursor.fetchall() if row[0]]
            total_teacher = len({
                (get_teacher_info(name).get("teacher_id") or _normalize_teacher_name(name).lower())
                for name in distinct_teachers
            })

            today = datetime.now(timezone(timedelta(hours=8))).date()
            cursor.execute(q(
                "SELECT COUNT(*) FROM recs WHERE DATE((time AT TIME ZONE 'UTC') AT TIME ZONE 'Asia/Shanghai') = %s",
                "SELECT COUNT(*) FROM recs WHERE DATE(datetime(time, '+8 hours')) = ?"
            ), (today,))
            today_count = cursor.fetchone()[0]

        return {"total_eval": total_eval, "total_teacher": total_teacher, "today": today_count}
    except Exception as e:
        logger.error(f"获取全局统计失败: {e}")
        return {"total_eval": 0, "total_teacher": 0, "today": 0}


def add_required_channel(channel_id: str) -> dict:
    """添加频道要求"""
    try:
        with _db.connect() as conn:
            cursor = conn.cursor()
            key = f"channel_{channel_id}"

            cursor.execute(_db.q("SELECT value FROM settings WHERE key = %s",
                                  "SELECT value FROM settings WHERE key = ?"), (key,))
            if cursor.fetchone():
                logger.warning(f"⚠️ 频道 {channel_id} 已添加过了")
                return {"success": False, "msg": f"❌ 频道 {channel_id} 已添加过了"}

            cursor.execute(
                _db.q("INSERT INTO settings (key, value) VALUES (%s, %s)",
                       "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)"),
                (key, channel_id)
            )
            conn.commit()

        logger.info(f"✅ 频道已添加: {channel_id}")
        return {"success": True, "msg": f"✅ 频道 {channel_id} 已添加"}
    except Exception as e:
        logger.error(f"添加频道失败: {e}")
        return {"success": False, "msg": f"❌ 添加频道失败: {str(e)}"}


def get_all_required_channels() -> list:
    """获取所有频道要求"""
    try:
        results = _db.query_all(
            "SELECT value FROM settings WHERE key LIKE %s",
            "SELECT value FROM settings WHERE key LIKE ?",
            ('channel_%',)
        )
        channels = [r[0] for r in results]
        logger.info(f"📋 获取到 {len(channels)} 个频道: {channels}")
        return channels
    except Exception as e:
        logger.error(f"获取频道列表失败: {e}")
        return []


def remove_required_channel(channel_id: str) -> dict:
    """移除频道要求"""
    try:
        _db.execute(
            "DELETE FROM settings WHERE key = %s",
            "DELETE FROM settings WHERE key = ?",
            (f"channel_{channel_id}",)
        )
        logger.info(f"✅ 频道已移除: {channel_id}")
        return {"success": True, "msg": f"✅ 频道 {channel_id} 已移除"}
    except Exception as e:
        logger.error(f"移除频道失败: {e}")
        return {"success": False, "msg": f"❌ 移除频道失败: {str(e)}"}


def set_start_message(message: str) -> None:
    """设置欢迎语"""
    try:
        _db.upsert(
            "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s",
            ("start_message", message, message),
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("start_message", message)
        )
        logger.info("✅ 欢迎语已设置")
    except Exception as e:
        logger.error(f"设置欢迎语失败: {e}")


def get_start_message(default: str = "") -> str:
    """获取欢迎语"""
    try:
        result = _db.query_one(
            "SELECT value FROM settings WHERE key = %s",
            "SELECT value FROM settings WHERE key = ?",
            ("start_message",)
        )
        return result[0] if result else default
    except Exception as e:
        logger.error(f"获取欢迎语失败: {e}")
        return default


def set_start_buttons(buttons: list) -> None:
    """保存欢迎语按钮（列表形式 [{"text": ..., "url": ...}, ...]）"""
    try:
        value = json.dumps(buttons, ensure_ascii=False)
        _db.upsert(
            "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s",
            ("start_message_buttons", value, value),
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("start_message_buttons", value)
        )
        logger.info(f"✅ 欢迎语按钮已保存，共 {len(buttons)} 个")
    except Exception as e:
        logger.error(f"保存欢迎语按钮失败: {e}")


def get_start_buttons() -> list:
    """获取欢迎语按钮列表"""
    try:
        result = _db.query_one(
            "SELECT value FROM settings WHERE key = %s",
            "SELECT value FROM settings WHERE key = ?",
            ("start_message_buttons",)
        )
        if result and result[0]:
            return json.loads(result[0])
        return []
    except Exception as e:
        logger.error(f"获取欢迎语按钮失败: {e}")
        return []


DEFAULT_AUTO_DELETE_DELAY = 600  # 默认 10 分钟（秒）


def set_auto_delete_delay(seconds: int) -> None:
    """设置群内消息自动删除时间（秒）"""
    try:
        value = str(int(seconds))
        _db.upsert(
            "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s",
            ("auto_delete_delay", value, value),
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("auto_delete_delay", value)
        )
        logger.info(f"✅ 自动删除时间已设置为 {seconds} 秒")
    except Exception as e:
        logger.error(f"设置自动删除时间失败: {e}")


def get_auto_delete_delay() -> int:
    """获取群内消息自动删除时间（秒），默认 10 分钟"""
    try:
        result = _db.query_one(
            "SELECT value FROM settings WHERE key = %s",
            "SELECT value FROM settings WHERE key = ?",
            ("auto_delete_delay",)
        )
        if result and result[0]:
            return int(result[0])
        return DEFAULT_AUTO_DELETE_DELAY
    except Exception as e:
        logger.error(f"获取自动删除时间失败: {e}")
        return DEFAULT_AUTO_DELETE_DELAY


def set_delete_user_messages(enabled: bool) -> None:
    """设置是否自动删除用户发出的消息"""
    try:
        value = "1" if enabled else "0"
        _db.upsert(
            "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s",
            ("delete_user_messages", value, value),
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("delete_user_messages", value)
        )
        logger.info(f"✅ 删除用户消息设置为: {'开启' if enabled else '关闭'}")
    except Exception as e:
        logger.error(f"设置删除用户消息失败: {e}")


def get_delete_user_messages() -> bool:
    """获取是否自动删除用户发出的消息（默认开启）"""
    try:
        result = _db.query_one(
            "SELECT value FROM settings WHERE key = %s",
            "SELECT value FROM settings WHERE key = ?",
            ("delete_user_messages",)
        )
        if result and result[0] is not None:
            return result[0] == "1"
        return True  # 默认开启
    except Exception as e:
        logger.error(f"获取删除用户消息设置失败: {e}")
        return True


def record_user(user_id: int, username: str = "", first_name: str = "") -> None:
    """记录使用过机器人的用户（用于广播）"""
    try:
        uname = username or ""
        fname = first_name or ""
        _db.upsert(
            """INSERT INTO users (user_id, username, first_name)
               VALUES (%s, %s, %s)
               ON CONFLICT (user_id) DO UPDATE SET username = %s, first_name = %s""",
            (user_id, uname, fname, uname, fname),
            "INSERT OR REPLACE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, uname, fname)
        )
    except Exception as e:
        logger.error(f"记录用户失败: {e}")


def get_all_user_ids() -> list:
    """获取所有曾使用过机器人的用户 ID"""
    try:
        rows = _db.query_all("SELECT user_id FROM users", "SELECT user_id FROM users")
        return [r[0] for r in rows]
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return []


def get_user_by_username(username: str) -> dict:
    """通过用户名从 users 表查找用户的 user_id 和 first_name（用于回退显示昵称/ID）"""
    try:
        row = _db.query_one(
            "SELECT user_id, first_name FROM users WHERE LOWER(username) = LOWER(%s)",
            "SELECT user_id, first_name FROM users WHERE LOWER(username) = LOWER(?)",
            (username,)
        )
        if row:
            return {"user_id": row[0], "first_name": row[1] or ""}
        return {}
    except Exception as e:
        logger.error(f"通过用户名查询用户失败: {e}")
        return {}


def set_teacher_info(name: str, nickname: str = "", teacher_id: str = "") -> None:
    """设置教师昵称和ID"""
    try:
        name = _normalize_teacher_name(name)
        if not name:
            return
        teacher_id = str(teacher_id).strip() if teacher_id else ""
        _db.upsert(
            """INSERT INTO teachers (name, nickname, teacher_id)
               VALUES (%s, %s, %s)
               ON CONFLICT (name) DO UPDATE SET nickname = %s, teacher_id = %s""",
            (name, nickname, teacher_id, nickname, teacher_id),
            "INSERT OR REPLACE INTO teachers (name, nickname, teacher_id) VALUES (?, ?, ?)",
            (name, nickname, teacher_id)
        )
        logger.info(f"✅ 教师 @{name} 信息已更新")
    except Exception as e:
        logger.error(f"设置教师信息失败: {e}")


def get_teacher_info(name: str) -> dict:
    """获取教师昵称和ID，未设置则返回空字符串"""
    try:
        name = _normalize_teacher_name(name)
        row = _db.query_one(
            "SELECT nickname, teacher_id FROM teachers WHERE LOWER(name) = LOWER(%s)",
            "SELECT nickname, teacher_id FROM teachers WHERE LOWER(name) = LOWER(?)",
            (name,)
        )
        if not row:
            row = _db.query_one(
                "SELECT nickname, teacher_id FROM teachers WHERE teacher_id = %s LIMIT 1",
                "SELECT nickname, teacher_id FROM teachers WHERE teacher_id = ? LIMIT 1",
                (name,)
            )
        if not row:
            row = _db.query_one(
                "SELECT nickname, teacher_id FROM teachers WHERE LOWER(nickname) = LOWER(%s) LIMIT 1",
                "SELECT nickname, teacher_id FROM teachers WHERE LOWER(nickname) = LOWER(?) LIMIT 1",
                (name,)
            )
        if row:
            return {"nickname": row[0] or "", "teacher_id": str(row[1] or "")}
        return {"nickname": "", "teacher_id": ""}
    except Exception as e:
        logger.error(f"获取教师信息失败: {e}")
        return {"nickname": "", "teacher_id": ""}


def get_teacher_reviews_page(teacher: str, page: int = 0, per_page: int = 5) -> list:
    """分页获取教师评价（用于"更多评价"按钮）"""
    try:
        offset = page * per_page
        aliases = _get_teacher_aliases(teacher)
        if not aliases:
            return []
        in_clause, alias_params = _build_in_clause_params(aliases)
        query = (
            f"SELECT id, user_id, recommend, reason, time FROM recs "
            f"WHERE teacher IN {in_clause} ORDER BY time DESC "
            f"LIMIT {'%s' if USE_POSTGRES else '?'} OFFSET {'%s' if USE_POSTGRES else '?'}"
        )
        return _db.query_all(query, query, alias_params + (per_page, offset))
    except Exception as e:
        logger.error(f"分页获取教师评价失败: {e}")
        return []


def get_encourage() -> str:
    """获取随机鼓励语"""
    encourages = [
        "✅ 评价提交成功！感谢您的反馈！",
        "🎉 评价已保存！您的意见很重要！",
        "👍 提交成功！帮助了其他同学！",
        "⭐ 评价完成！谢谢您的参与！",
        "🌟 成功保存！您的建议已记录！"
    ]
    return random.choice(encourages)


# ==================== 教师数据删除函数 ====================

def delete_teacher_data_from_db(teacher: str) -> dict:
    """
    删除某个教师的所有评价数据

    Args:
        teacher: 教师名称

    Returns:
        删除结果
    """
    try:
        with _db.connect() as conn:
            cursor = conn.cursor()
            aliases = _get_teacher_aliases_with_conn(conn, teacher)
            if not aliases:
                aliases = [_normalize_teacher_name(teacher)]
            in_clause, alias_params = _build_in_clause_params(aliases)

            cursor.execute(f"SELECT COUNT(*) FROM recs WHERE teacher IN {in_clause}", alias_params)
            total = cursor.fetchone()[0]

            cursor.execute(f"DELETE FROM recs WHERE teacher IN {in_clause}", alias_params)
            cursor.execute(f"DELETE FROM teachers WHERE name IN {in_clause}", alias_params)
            conn.commit()

        logger.warning(f"🗑️ 已删除教师 @{teacher} 的 {total} 条评价数据")
        return {
            "success": True,
            "msg": f"✅ 教师数据已删除\n\n教师: @{teacher}\n删除数: {total} 条评价\n\n数据已从数据库中永久删除"
        }
    except Exception as e:
        logger.error(f"删除教师数据失败: {e}")
        return {"success": False, "msg": f"❌ 删除失败: {str(e)}"}


def delete_user_rating(teacher: str, user_id: int) -> dict:
    """
    删除某个用户对某个教师的评价

    Args:
        teacher: 教师名称
        user_id: 用户 ID

    Returns:
        删除结果
    """
    try:
        aliases = _get_teacher_aliases(teacher)
        if not aliases:
            return {"success": False, "msg": "❌ 未找到教师记录"}
        in_clause, alias_params = _build_in_clause_params(aliases)
        query = (
            f"DELETE FROM recs WHERE teacher IN {in_clause} "
            f"AND user_id = {'%s' if USE_POSTGRES else '?'}"
        )
        _db.execute(query, query, alias_params + (user_id,))
        logger.warning(f"🗑️ 已删除用户 {user_id} 对教师 @{teacher} 的评价")
        return {"success": True, "msg": "✅ 评价已删除"}
    except Exception as e:
        logger.error(f"删除评价失败: {e}")
        return {"success": False, "msg": f"❌ 删除失败: {str(e)}"}


def get_teacher_detail(teacher: str) -> Optional[dict]:
    """
    获取教师的评价详情（推荐数、不推荐数及理由列表）

    Args:
        teacher: 教师名称

    Returns:
        dict with keys 'yes', 'no', 'reasons', or None if no records exist
    """
    try:
        with _db.connect() as conn:
            cursor = conn.cursor()
            aliases = _get_teacher_aliases_with_conn(conn, teacher)
            if not aliases:
                return None
            in_clause, alias_params = _build_in_clause_params(aliases)

            cursor.execute(f"SELECT COUNT(*) FROM recs WHERE teacher IN {in_clause}", alias_params)
            total = cursor.fetchone()[0]

            if total == 0:
                return None

            cursor.execute(
                f"SELECT COUNT(*) FROM recs WHERE teacher IN {in_clause} AND recommend = 1",
                alias_params
            )
            yes_count = cursor.fetchone()[0]

            cursor.execute(
                f"SELECT COUNT(*) FROM recs WHERE teacher IN {in_clause} AND recommend = 0",
                alias_params
            )
            no_count = cursor.fetchone()[0]

            cursor.execute(
                f"SELECT reason FROM recs WHERE teacher IN {in_clause} ORDER BY time DESC",
                alias_params
            )
            reasons = [row[0] for row in cursor.fetchall()]

        return {"yes": yes_count, "no": no_count, "reasons": reasons}
    except Exception as e:
        logger.error(f"获取教师详情失败: {e}")
        return None


def get_teacher_all_ratings(teacher: str) -> list:
    """
    获取某个教师的所有评价

    Args:
        teacher: 教师名称

    Returns:
        评价列表
    """
    try:
        aliases = _get_teacher_aliases(teacher)
        if not aliases:
            return []
        in_clause, alias_params = _build_in_clause_params(aliases)
        query = f"SELECT id, user_id, recommend, reason, time FROM recs WHERE teacher IN {in_clause} ORDER BY time DESC"
        return _db.query_all(query, query, alias_params)
    except Exception as e:
        logger.error(f"获取教师评价失败: {e}")
        return []


def get_leaderboard(limit: int = 10, order_by: str = "recommend") -> list:
    """
    获取教师排行榜

    Args:
        limit: 返回的教师数量，默认 10
        order_by: 排序字段，支持 recommend / not_recommend

    Returns:
        列表，每项为 dict: teacher, total, recommend, not_recommend, recommend_pct, not_recommend_pct
    """
    try:
        if order_by not in {"recommend", "not_recommend"}:
            order_by = "recommend"

        rows = _db.query_all(
            """SELECT teacher,
                      COUNT(*) AS total,
                      SUM(CASE WHEN recommend = 1 THEN 1 ELSE 0 END) AS recommend_count,
                      SUM(CASE WHEN recommend = 0 THEN 1 ELSE 0 END) AS not_recommend_count
               FROM recs
               GROUP BY teacher""",
            """SELECT teacher,
                      COUNT(*) AS total,
                      SUM(CASE WHEN recommend = 1 THEN 1 ELSE 0 END) AS recommend_count,
                      SUM(CASE WHEN recommend = 0 THEN 1 ELSE 0 END) AS not_recommend_count
               FROM recs
               GROUP BY teacher"""
        )
        merged = {}
        for row in rows:
            teacher_name = row[0]
            info = get_teacher_info(teacher_name)
            key = info.get("teacher_id") or _normalize_teacher_name(teacher_name).lower()
            entry = merged.setdefault(key, {
                "teacher": teacher_name,
                "total": 0,
                "recommend": 0,
                "not_recommend": 0,
            })
            entry["total"] += row[1] or 0
            entry["recommend"] += row[2] or 0
            entry["not_recommend"] += row[3] or 0
            if (row[1] or 0) > entry.get("_best_total", -1):
                entry["teacher"] = teacher_name
                entry["_best_total"] = row[1] or 0

        result = []
        for entry in merged.values():
            total = entry["total"]
            result.append({
                "teacher": entry["teacher"],
                "total": total,
                "recommend": entry["recommend"],
                "not_recommend": entry["not_recommend"],
                "recommend_pct": int(entry["recommend"] / total * 100) if total > 0 else 0,
                "not_recommend_pct": int(entry["not_recommend"] / total * 100) if total > 0 else 0,
            })

        result.sort(key=lambda item: (item[order_by], item["total"]), reverse=True)
        return result[:limit]
    except Exception as e:
        logger.error(f"获取排行榜失败: {e}")
        return []


def delete_rating_by_id(rating_id: str, teacher: str) -> dict:
    """删除指定 ID 的评价"""
    try:
        aliases = _get_teacher_aliases(teacher)
        if not aliases:
            return {"success": False, "msg": "❌ 未找到教师记录"}
        in_clause, alias_params = _build_in_clause_params(aliases)
        query = (
            f"DELETE FROM recs WHERE id = {'%s' if USE_POSTGRES else '?'} "
            f"AND teacher IN {in_clause}"
        )
        _db.execute(query, query, (int(rating_id),) + alias_params)
        logger.warning(f"🗑️ 删除了评价 ID: {rating_id}")
        return {"success": True, "msg": "✅ 评价已删除"}
    except Exception as e:
        logger.error(f"删除评价失败: {e}")
        return {"success": False, "msg": f"❌ 删除失败: {str(e)}"}


# ==================== 黑名单管理 ====================

def add_to_blacklist(user_id: int, reason: str = "") -> dict:
    """将用户加入黑名单"""
    try:
        _db.upsert(
            """INSERT INTO blacklist (user_id, reason)
               VALUES (%s, %s)
               ON CONFLICT (user_id) DO UPDATE SET reason = %s""",
            (user_id, reason, reason),
            "INSERT OR REPLACE INTO blacklist (user_id, reason) VALUES (?, ?)",
            (user_id, reason)
        )
        logger.warning(f"🚫 用户 {user_id} 已被加入黑名单，原因：{reason}")
        return {"success": True, "msg": f"✅ 用户 {user_id} 已被加入黑名单"}
    except Exception as e:
        logger.error(f"加入黑名单失败: {e}")
        return {"success": False, "msg": f"❌ 操作失败: {str(e)}"}


def remove_from_blacklist(user_id: int) -> dict:
    """将用户从黑名单中移除"""
    try:
        _db.execute(
            "DELETE FROM blacklist WHERE user_id = %s",
            "DELETE FROM blacklist WHERE user_id = ?",
            (user_id,)
        )
        logger.info(f"✅ 用户 {user_id} 已从黑名单中移除")
        return {"success": True, "msg": f"✅ 用户 {user_id} 已从黑名单中移除"}
    except Exception as e:
        logger.error(f"移除黑名单失败: {e}")
        return {"success": False, "msg": f"❌ 操作失败: {str(e)}"}


def is_user_blacklisted(user_id: int) -> bool:
    """检查用户是否在黑名单中"""
    try:
        result = _db.query_one(
            "SELECT user_id FROM blacklist WHERE user_id = %s",
            "SELECT user_id FROM blacklist WHERE user_id = ?",
            (user_id,)
        )
        return result is not None
    except Exception as e:
        logger.error(f"检查黑名单失败: {e}")
        return False


def get_all_blacklisted_users() -> list:
    """获取所有黑名单用户"""
    try:
        rows = _db.query_all(
            "SELECT user_id, reason, banned_at FROM blacklist ORDER BY banned_at DESC",
            "SELECT user_id, reason, banned_at FROM blacklist ORDER BY banned_at DESC"
        )
        return [{"user_id": r[0], "reason": r[1] or "", "banned_at": str(r[2])[:19] if r[2] else ""} for r in rows]
    except Exception as e:
        logger.error(f"获取黑名单失败: {e}")
        return []


def search_teachers(keyword: str) -> list:
    """模糊搜索教师名称（从 recs 表中查找包含关键词的教师）"""
    try:
        keyword = _normalize_teacher_name(keyword)
        pattern = f"%{keyword}%"
        rec_rows = _db.query_all(
            "SELECT DISTINCT teacher FROM recs WHERE LOWER(teacher) LIKE LOWER(%s) ORDER BY teacher LIMIT 20",
            "SELECT DISTINCT teacher FROM recs WHERE LOWER(teacher) LIKE LOWER(?) ORDER BY teacher LIMIT 20",
            (pattern,)
        )
        teacher_rows = _db.query_all(
            "SELECT name FROM teachers WHERE LOWER(name) LIKE LOWER(%s) OR LOWER(nickname) LIKE LOWER(%s) OR teacher_id LIKE %s ORDER BY name LIMIT 20",
            "SELECT name FROM teachers WHERE LOWER(name) LIKE LOWER(?) OR LOWER(nickname) LIKE LOWER(?) OR teacher_id LIKE ? ORDER BY name LIMIT 20",
            (pattern, pattern, pattern)
        )

        results = []
        seen = set()
        for row in list(rec_rows) + list(teacher_rows):
            name = row[0]
            info = get_teacher_info(name)
            key = info.get("teacher_id") or _normalize_teacher_name(name).lower()
            if key in seen:
                continue
            seen.add(key)
            results.append(name)
        return results[:20]
    except Exception as e:
        logger.error(f"搜索教师失败: {e}")
        return []


def get_teacher_score_averages(teacher: str) -> dict:
    """获取教师的三项评分平均值（仅统计非 NULL 的评分记录）"""
    try:
        aliases = _get_teacher_aliases(teacher)
        if not aliases:
            return {"teaching": None, "grading": None, "difficulty": None,
                    "teaching_count": 0, "grading_count": 0, "difficulty_count": 0}
        in_clause, alias_params = _build_in_clause_params(aliases)
        query = (
            f"SELECT AVG(score_teaching), AVG(score_grading), AVG(score_difficulty),"
            f" COUNT(score_teaching), COUNT(score_grading), COUNT(score_difficulty)"
            f" FROM recs WHERE teacher IN {in_clause}"
        )
        row = _db.query_one(query, query, alias_params)
        if row:
            def fmt(val):
                return round(float(val), 1) if val is not None else None
            return {
                "teaching": fmt(row[0]),
                "grading": fmt(row[1]),
                "difficulty": fmt(row[2]),
                "teaching_count": row[3] or 0,
                "grading_count": row[4] or 0,
                "difficulty_count": row[5] or 0,
            }
        return {"teaching": None, "grading": None, "difficulty": None,
                "teaching_count": 0, "grading_count": 0, "difficulty_count": 0}
    except Exception as e:
        logger.error(f"获取教师评分均值失败: {e}")
        return {"teaching": None, "grading": None, "difficulty": None,
                "teaching_count": 0, "grading_count": 0, "difficulty_count": 0}


# ==================== 普通管理员（sub_admin）管理 ====================

def add_sub_admin(user_id: int, username: str = "") -> dict:
    """添加普通管理员"""
    try:
        _db.execute(
            "INSERT INTO sub_admins (user_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            "INSERT OR IGNORE INTO sub_admins (user_id, username) VALUES (?, ?)",
            (user_id, username or "")
        )
        logger.info(f"✅ 已添加普通管理员: {user_id}")
        return {"success": True, "msg": f"✅ 已添加普通管理员 ID: <code>{user_id}</code>"}
    except Exception as e:
        logger.error(f"添加普通管理员失败: {e}")
        return {"success": False, "msg": f"❌ 添加失败: {e}"}


def remove_sub_admin(user_id: int) -> dict:
    """移除普通管理员"""
    try:
        _db.execute(
            "DELETE FROM sub_admins WHERE user_id = %s",
            "DELETE FROM sub_admins WHERE user_id = ?",
            (user_id,)
        )
        logger.info(f"✅ 已移除普通管理员: {user_id}")
        return {"success": True, "msg": f"✅ 已移除普通管理员 ID: <code>{user_id}</code>"}
    except Exception as e:
        logger.error(f"移除普通管理员失败: {e}")
        return {"success": False, "msg": f"❌ 移除失败: {e}"}


def is_sub_admin(user_id: int) -> bool:
    """判断用户是否为普通管理员"""
    try:
        row = _db.query_one(
            "SELECT user_id FROM sub_admins WHERE user_id = %s",
            "SELECT user_id FROM sub_admins WHERE user_id = ?",
            (user_id,)
        )
        return row is not None
    except Exception as e:
        logger.error(f"检查普通管理员失败: {e}")
        return False


def get_all_sub_admins() -> list:
    """获取所有普通管理员列表"""
    try:
        rows = _db.query_all(
            "SELECT user_id, username, added_at FROM sub_admins ORDER BY added_at",
            "SELECT user_id, username, added_at FROM sub_admins ORDER BY added_at"
        )
        return [{"user_id": r[0], "username": r[1], "added_at": r[2]} for r in rows]
    except Exception as e:
        logger.error(f"获取普通管理员列表失败: {e}")
        return []
