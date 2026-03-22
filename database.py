# database.py
"""
数据库操作模块 - 支持 SQLite 和 PostgreSQL
"""

import sqlite3
import logging
import os
from datetime import datetime
from config import MIN_REASON_LENGTH

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

logger = logging.getLogger(__name__)

# 检查数据库类型
DB_TYPE = os.getenv("DATABASE_URL")
USE_POSTGRES = DB_TYPE is not None and HAS_POSTGRES

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    from config import DATABASE_PATH

def get_connection():
    """获取数据库连接"""
    if USE_POSTGRES:
        try:
            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            return conn
        except Exception as e:
            logger.error(f"PostgreSQL 连接失败: {e}")
            raise
    else:
        # SQLite
        db_dir = os.path.dirname(DATABASE_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """初始化数据库"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            # PostgreSQL 表定义
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recs (
                    id SERIAL PRIMARY KEY,
                    teacher TEXT NOT NULL,
                    user_id BIGINT NOT NULL,
                    recommend INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(teacher, user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_teacher ON recs(teacher)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON recs(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_time ON recs(time)")
        else:
            # SQLite 表定义
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    recommend INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(teacher, user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_teacher ON recs(teacher)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON recs(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_time ON recs(time)")
        
        conn.commit()
        conn.close()
        
        db_info = "PostgreSQL" if USE_POSTGRES else "SQLite"
        logger.info(f"✅ {db_info} 数据库初始化成功")
    
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


def check_user_rated_teacher(teacher: str, user_id: int) -> bool:
    """检查用户是否已评价该教师"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM recs WHERE teacher = %s AND user_id = %s" if USE_POSTGRES else "SELECT id FROM recs WHERE teacher = ? AND user_id = ?", (teacher, user_id))
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    except Exception as e:
        logger.error(f"检查评价记录时出错: {e}")
        return False


def add_evaluation(teacher: str, recommend: int, reason: str, user_id: int) -> dict:
    """添加评价"""
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
        conn = get_connection()
        cursor = conn.cursor()
        
        sql = "INSERT INTO recs (teacher, user_id, recommend, reason) VALUES (%s, %s, %s, %s)" if USE_POSTGRES else "INSERT INTO recs (teacher, user_id, recommend, reason) VALUES (?, ?, ?, ?)"
        cursor.execute(sql, (teacher, user_id, recommend, reason))
        
        conn.commit()
        conn.close()
        
        logger.info(f"用户 {user_id} 成功评价了 {teacher}")
        return {
            "success": True,
            "msg": "✅ 评价提交成功！\n\n感谢您的反馈！"
        }
    
    except Exception as e:
        logger.error(f"添加评价失败: {e}")
        return {
            "success": False,
            "msg": f"❌ 提交失败: {str(e)}"
        }


def get_teacher_stats(teacher: str) -> dict:
    """获取教师的评价统计"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        sql_count = "SELECT COUNT(*) FROM recs WHERE teacher = %s" if USE_POSTGRES else "SELECT COUNT(*) FROM recs WHERE teacher = ?"
        sql_rec = "SELECT COUNT(*) FROM recs WHERE teacher = %s AND recommend = 1" if USE_POSTGRES else "SELECT COUNT(*) FROM recs WHERE teacher = ? AND recommend = 1"
        sql_not_rec = "SELECT COUNT(*) FROM recs WHERE teacher = %s AND recommend = 0" if USE_POSTGRES else "SELECT COUNT(*) FROM recs WHERE teacher = ? AND recommend = 0"
        sql_latest = "SELECT user_id, recommend, reason, time FROM recs WHERE teacher = %s ORDER BY time DESC LIMIT 3" if USE_POSTGRES else "SELECT user_id, recommend, reason, time FROM recs WHERE teacher = ? ORDER BY time DESC LIMIT 3"
        
        cursor.execute(sql_count, (teacher,))
        total = cursor.fetchone()[0]
        
        cursor.execute(sql_rec, (teacher,))
        recommend_count = cursor.fetchone()[0]
        
        cursor.execute(sql_not_rec, (teacher,))
        not_recommend_count = cursor.fetchone()[0]
        
        cursor.execute(sql_latest, (teacher,))
        latest = cursor.fetchall()
        
        conn.close()
        
        return {
            "teacher": teacher,
            "total": total,
            "recommend": recommend_count,
            "not_recommend": not_recommend_count,
            "latest": latest
        }
    except Exception as e:
        logger.error(f"获取教师统计失败: {e}")
        return {
            "teacher": teacher,
            "total": 0,
            "recommend": 0,
            "not_recommend": 0,
            "latest": []
        }


def get_global_stats() -> dict:
    """获取全局统计"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM recs")
        total_eval = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT teacher) FROM recs")
        total_teacher = cursor.fetchone()[0]
        
        today = datetime.now().date()
        sql = "SELECT COUNT(*) FROM recs WHERE DATE(time) = %s" if USE_POSTGRES else "SELECT COUNT(*) FROM recs WHERE DATE(time) = ?"
        cursor.execute(sql, (today,))
        today_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_eval": total_eval,
            "total_teacher": total_teacher,
            "today": today_count
        }
    except Exception as e:
        logger.error(f"获取全局统计失败: {e}")
        return {
            "total_eval": 0,
            "total_teacher": 0,
            "today": 0
        }


def set_required_channel(channel_id: str):
    """设置频道要求"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        sql = "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s" if USE_POSTGRES else "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)"
        
        if USE_POSTGRES:
            cursor.execute(sql, ("required_channel", channel_id, channel_id))
        else:
            cursor.execute(sql, ("required_channel", channel_id))
        
        conn.commit()
        conn.close()
        logger.info(f"频道要求已设置: {channel_id}")
    except Exception as e:
        logger.error(f"设置频道要求失败: {e}")


def get_required_channel() -> str:
    """获取频道要求"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        sql = "SELECT value FROM settings WHERE key = %s" if USE_POSTGRES else "SELECT value FROM settings WHERE key = ?"
        cursor.execute(sql, ("required_channel",))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else ""
    except Exception as e:
        logger.error(f"获取频道要求失败: {e}")
        return ""


def set_start_message(message: str):
    """设置欢迎语"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        sql = "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s" if USE_POSTGRES else "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)"
        
        if USE_POSTGRES:
            cursor.execute(sql, ("start_message", message, message))
        else:
            cursor.execute(sql, ("start_message", message))
        
        conn.commit()
        conn.close()
        logger.info("欢迎语已设置")
    except Exception as e:
        logger.error(f"设置欢迎语失败: {e}")


def get_start_message(default: str = "") -> str:
    """获取欢迎语"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        sql = "SELECT value FROM settings WHERE key = %s" if USE_POSTGRES else "SELECT value FROM settings WHERE key = ?"
        cursor.execute(sql, ("start_message",))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else default
    except Exception as e:
        logger.error(f"获取欢迎语失败: {e}")
        return default


def get_encourage() -> str:
    """获取随机鼓励语"""
    encourages = [
        "✅ 评价提交成功！感谢您的反馈！",
        "🎉 评价已保存！您的意见很重要！",
        "👍 提交成功！帮助了其他同学！",
        "⭐ 评价完成！谢谢您的参与！",
        "🌟 成功保存！您的建议已记录！"
    ]
    
    import random
    return random.choice(encourages)