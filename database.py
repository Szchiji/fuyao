# database.py
"""
数据库操作模块
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from config import DATABASE_PATH, MIN_REASON_LENGTH

logger = logging.getLogger(__name__)

def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 创建评价表
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
    
    # 创建设置表
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
    
    conn.commit()
    conn.close()
    logger.info("✅ 数据库初始化成功")


def check_user_rated_teacher(teacher: str, user_id: int) -> bool:
    """检查用户是否已评价该教师"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM recs WHERE teacher = ? AND user_id = ?", (teacher, user_id))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None


def add_evaluation(teacher: str, recommend: int, reason: str, user_id: int) -> dict:
    """
    添加评价
    
    Returns:
        {"success": bool, "msg": str}
    """
    # 验证理由长度
    if len(reason.strip()) < MIN_REASON_LENGTH:
        return {
            "success": False,
            "msg": f"❌ 理由太短！至少需要 {MIN_REASON_LENGTH} 个字\n\n您填写的: {len(reason)} 个字"
        }
    
    # 检查是否已评价
    if check_user_rated_teacher(teacher, user_id):
        return {
            "success": False,
            "msg": f"❌ 您已经评价过 @{teacher} 了\n\n每个教师只能评价一次"
        }
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO recs (teacher, user_id, recommend, reason)
            VALUES (?, ?, ?, ?)
        """, (teacher, user_id, recommend, reason))
        
        conn.commit()
        conn.close()
        
        logger.info(f"用户 {user_id} 成功评价了 {teacher}")
        return {
            "success": True,
            "msg": "✅ 评价提交成功！\n\n感谢您的反馈！"
        }
    
    except sqlite3.IntegrityError:
        return {
            "success": False,
            "msg": f"❌ 您已经评价过 @{teacher} 了\n\n每个教师只能评价一次"
        }
    except Exception as e:
        logger.error(f"添加评价失败: {e}")
        return {
            "success": False,
            "msg": f"❌ 提交失败: {str(e)}"
        }


def get_teacher_stats(teacher: str) -> dict:
    """获取教师的评价统计"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取总评价数
    cursor.execute("SELECT COUNT(*) FROM recs WHERE teacher = ?", (teacher,))
    total = cursor.fetchone()[0]
    
    # 获取推荐数
    cursor.execute("SELECT COUNT(*) FROM recs WHERE teacher = ? AND recommend = 1", (teacher,))
    recommend_count = cursor.fetchone()[0]
    
    # 获取不推荐数
    cursor.execute("SELECT COUNT(*) FROM recs WHERE teacher = ? AND recommend = 0", (teacher,))
    not_recommend_count = cursor.fetchone()[0]
    
    # 获取最新的评价
    cursor.execute("""
        SELECT user_id, recommend, reason, time 
        FROM recs 
        WHERE teacher = ? 
        ORDER BY time DESC 
        LIMIT 3
    """, (teacher,))
    latest = cursor.fetchall()
    
    conn.close()
    
    return {
        "teacher": teacher,
        "total": total,
        "recommend": recommend_count,
        "not_recommend": not_recommend_count,
        "latest": latest
    }


def get_global_stats() -> dict:
    """获取全局统计"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 总评价数
    cursor.execute("SELECT COUNT(*) FROM recs")
    total_eval = cursor.fetchone()[0]
    
    # 评价教师数
    cursor.execute("SELECT COUNT(DISTINCT teacher) FROM recs")
    total_teacher = cursor.fetchone()[0]
    
    # 今日评价
    today = datetime.now().date()
    cursor.execute(
        "SELECT COUNT(*) FROM recs WHERE DATE(time) = ?",
        (today,)
    )
    today_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_eval": total_eval,
        "total_teacher": total_teacher,
        "today": today_count
    }


def set_required_channel(channel_id: str):
    """设置频道要求"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if channel_id:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ("required_channel", channel_id)
        )
    else:
        cursor.execute("DELETE FROM settings WHERE key = ?", ("required_channel",))
    
    conn.commit()
    conn.close()


def get_required_channel() -> str:
    """获取频道要求"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT value FROM settings WHERE key = ?", ("required_channel",))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else ""


def set_start_message(message: str):
    """设置欢迎语"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("start_message", message)
    )
    
    conn.commit()
    conn.close()


def get_start_message(default: str = "") -> str:
    """获取欢迎语"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT value FROM settings WHERE key = ?", ("start_message",))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else default


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